"""Agent instruction loader — markdown protocols for autonomous agents."""

from __future__ import annotations

from pathlib import Path

INSTRUCTIONS_DIR = Path(__file__).resolve().parent

# Agent ID → instruction filename
INSTRUCTION_FILES: dict[str, str] = {
    "core.monitor": "monitor.md",
    "core.forensics": "forensics.md",
    "core.execution": "execution.md",
    "skill.recon_osint": "recon_osint.md",
    "skill.timing_analysis": "timing_analysis.md",
    "skill.trx_drainer": "trx_drainer_forensics.md",
    "skill.evm_drainer": "evm_drainer_forensics.md",
    "skill.apeterminal_drainer": "apeterminal_forensics.md",
    "skill.solana_drainer": "solana_drainer_forensics.md",
    "skill.vanilla_drainer": "vanilla_drainer_forensics.md",
    "skill.permit_farming": "permit_farming_forensics.md",
    "skill.create2_drainer": "create2_drainer_forensics.md",
    "skill.dual_mode": "dual_mode.md",
}


def load_instruction(agent_id: str) -> str:
    """Load markdown instruction protocol for an agent."""
    filename = INSTRUCTION_FILES.get(agent_id)
    if not filename:
        raise KeyError(f"No instruction file mapped for agent: {agent_id}")
    path = INSTRUCTIONS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Instruction file missing: {path}")
    return path.read_text(encoding="utf-8")


def list_agents() -> list[str]:
    return list(INSTRUCTION_FILES.keys())
