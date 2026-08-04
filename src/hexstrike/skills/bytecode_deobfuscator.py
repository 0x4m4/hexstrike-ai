"""skill.bytecode_deobfuscator — contract bytecode analysis and pattern extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.integrations.rpc_client import StealthRpcClient
from hexstrike.paths import RPC_CONFIG

# Common EVM opcode markers (hex without 0x prefix in bytecode string)
DELEGATECALL = "f4"
SELFDESTRUCT = "ff"
CREATE2 = "f5"
EIP1167_MINIMAL_PROXY = "363d3d373d3d3d363d73"


@dataclass
class BytecodeDeobfuscatorSkill:
    """Analyze contract bytecode for proxies, delegates, and sweep patterns."""

    bus: ContextBus
    config_path: Any = RPC_CONFIG

    def fetch_bytecode(self, address: str) -> str:
        client = StealthRpcClient(self.config_path)
        _, resp = client.call("eth_getCode", [address, "latest"], timeout=10.0)
        code = resp.get("result") or "0x"
        return code.lower()

    def analyze(self, address: str) -> dict[str, Any]:
        raw = self.fetch_bytecode(address)
        body = raw[2:] if raw.startswith("0x") else raw

        findings: list[str] = []
        if EIP1167_MINIMAL_PROXY in body:
            findings.append("eip1167_minimal_proxy")
        if DELEGATECALL in body:
            findings.append("contains_delegatecall")
        if SELFDESTRUCT in body:
            findings.append("contains_selfdestruct")
        if CREATE2 in body:
            findings.append("contains_create2")

        impl_match = re.search(r"363d3d373d3d3d363d73([0-9a-f]{40})5af43d", body)
        implementation = f"0x{impl_match.group(1)}" if impl_match else None

        result = {
            "address": address.lower(),
            "bytecode_length": len(body) // 2,
            "is_contract": len(body) > 0,
            "findings": findings,
            "implementation_address": implementation,
            "risk_score": min(10, len(findings) * 2 + (3 if implementation else 0)),
        }
        self.bus.publish("skill.bytecode.analyzed", result, source="skill.bytecode_deobfuscator")
        return result

    def deobfuscate_proxy(self, address: str) -> dict[str, Any]:
        base = self.analyze(address)
        if base.get("implementation_address"):
            impl_analysis = self.analyze(base["implementation_address"])
            base["implementation_analysis"] = impl_analysis
        return base
