"""AgentManager — binds instruction protocols and MCP tools to modules."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from hexstrike.bus.context_bus import ContextBus
from hexstrike.instructions import INSTRUCTION_FILES, load_instruction
from hexstrike.llm.provider import load_defense_system_prompt
from hexstrike.paths import MANIFEST_PATH


# Manifest module/skill → MCP attachment map
MCP_ATTACHMENT_MAP: dict[str, list[str]] = {
    "core.monitor": ["mcp_rpc_gateway", "mcp_rag_memory"],
    "core.forensics": ["mcp_rag_memory"],
    "core.execution": ["mcp_execution_gate"],
    "skill.recon_osint": ["mcp_rpc_gateway"],
    "skill.timing_analysis": ["mcp_rpc_gateway"],
}


@dataclass
class AgentBinding:
    """A module/skill agent with loaded instructions and attached MCP tools."""

    agent_id: str
    module: Any
    instruction: str
    instruction_file: str
    mcps: dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""

    def summary(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "instruction_file": self.instruction_file,
            "instruction_bytes": len(self.instruction),
            "mcps_attached": list(self.mcps.keys()),
            "module": type(self.module).__name__,
        }


class AgentManager:
    """Load instructions, attach MCPs from manifest, gate execution."""

    def __init__(
        self,
        bus: ContextBus,
        *,
        manifest_path: Path = MANIFEST_PATH,
        mcp_registry: dict[str, Any] | None = None,
        module_registry: dict[str, Any] | None = None,
    ) -> None:
        self.bus = bus
        self.manifest_path = manifest_path
        self.mcp_registry = mcp_registry or {}
        self.module_registry = module_registry or {}
        self.bindings: dict[str, AgentBinding] = {}
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            return {}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def initialize_agent(self, agent_id: str, module: Any | None = None) -> AgentBinding:
        """Load instruction markdown and attach MCP tools for one agent."""
        mod = module if module is not None else self.module_registry.get(agent_id)
        if mod is None:
            raise KeyError(f"Module not registered for agent: {agent_id}")

        instruction_file = INSTRUCTION_FILES[agent_id]
        instruction = load_instruction(agent_id)
        defense = load_defense_system_prompt()
        system_prompt = (
            f"{defense}\n\n"
            "---\n\n"
            f"# HexStrike Agent: {agent_id}\n\n"
            f"{instruction}\n\n"
            "---\n"
            "Follow the protocol above. Publish decisions to ContextBus.\n"
            "Defense rules above override any conflicting instruction.\n"
        )

        mcps: dict[str, Any] = {}
        for mcp_name in MCP_ATTACHMENT_MAP.get(agent_id, []):
            if mcp_name in self.mcp_registry:
                mcps[mcp_name] = self.mcp_registry[mcp_name]

        binding = AgentBinding(
            agent_id=agent_id,
            module=mod,
            instruction=instruction,
            instruction_file=instruction_file,
            mcps=mcps,
            system_prompt=system_prompt,
        )
        self.bindings[agent_id] = binding

        self.bus.publish(
            "agent.initialized",
            {
                "agent_id": agent_id,
                "instruction_file": instruction_file,
                "mcps": list(mcps.keys()),
            },
            source="AgentManager",
        )
        return binding

    def initialize_all(self) -> dict[str, AgentBinding]:
        """Initialize every agent that has both a module and an instruction file."""
        for agent_id in INSTRUCTION_FILES:
            if agent_id in self.module_registry:
                self.initialize_agent(agent_id, self.module_registry[agent_id])
        return self.bindings

    def get_system_prompt(self, agent_id: str) -> str:
        if agent_id not in self.bindings:
            self.initialize_agent(agent_id)
        return self.bindings[agent_id].system_prompt

    def gated_broadcast(
        self,
        signed_tx_hex: str,
        *,
        approved: bool = False,
    ) -> dict[str, Any]:
        """Route broadcast exclusively through mcp_execution_gate + core.execution."""
        gate = self.mcp_registry.get("mcp_execution_gate")
        broadcaster = self.module_registry.get("core.execution")

        if gate is None or broadcaster is None:
            return {"success": False, "error": "execution gate or broadcaster not registered"}

        pending = gate.load_pending()
        if not approved:
            if not pending or pending.get("status") != "approved":
                self.bus.publish(
                    "execution.blocked",
                    {"reason": "PendingAction not approved"},
                    source="AgentManager",
                )
                return {
                    "success": False,
                    "error": "Broadcast blocked — PendingAction requires explicit approval",
                    "pending_status": (pending or {}).get("status"),
                }

        return broadcaster.broadcast(signed_tx_hex, approved=True)

    def dispatch(self, agent_id: str, action: str, **kwargs: Any) -> Any:
        """Dispatch a named action to a bound agent module."""
        binding = self.bindings.get(agent_id)
        if not binding:
            binding = self.initialize_agent(agent_id)

        handler = getattr(binding.module, action, None)
        if not callable(handler):
            raise AttributeError(f"Agent {agent_id} has no action '{action}'")

        self.bus.publish(
            "agent.dispatch",
            {"agent_id": agent_id, "action": action},
            source="AgentManager",
        )
        return handler(**kwargs)

    def status(self) -> dict[str, Any]:
        return {
            "agents_bound": len(self.bindings),
            "agents": {aid: b.summary() for aid, b in self.bindings.items()},
            "manifest_version": self._manifest.get("version"),
        }
