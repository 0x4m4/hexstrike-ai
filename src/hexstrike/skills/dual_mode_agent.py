"""Dual-Mode agent — defense audit + sandbox offense PoC orchestration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from hexstrike.bus.context_bus import ContextBus
from hexstrike.llm.provider import LocalLlmProvider
from hexstrike.paths import ROOT
from hexstrike.skills.contract_toolchain import ContractToolchain, ToolResult

Mode = Literal["defense", "offense", "forensics"]

ARTIFACT_DIR = ROOT / "artifacts" / "dual-mode"


def _normalize_mode(mode: str) -> Mode:
    m = (mode or "defense").strip().lower()
    if m in ("offense", "attack", "redteam", "red-team"):
        return "offense"
    if m == "forensics":
        return "forensics"
    return "defense"


def _limits_disabled() -> bool:
    return os.environ.get("HEXSTRIKE_LIMITS_DISABLED", os.environ.get("DUAL_MODE_LIMITS_DISABLED", "")).lower() in (
        "1",
        "true",
        "yes",
    )


def _offense_allowed() -> bool:
    if _limits_disabled():
        os.environ.setdefault("HEXSTRIKE_SANDBOX", "1")
        return True
    return os.environ.get("HEXSTRIKE_SANDBOX", "").lower() in ("1", "true", "yes")


@dataclass
class DualModeAgent:
    """Defense + offense contract expert wired to HexStrike bus + optional LLM."""

    bus: ContextBus
    llm: LocalLlmProvider | None = None
    toolchain: ContractToolchain = field(default_factory=ContractToolchain)
    artifact_dir: Path = ARTIFACT_DIR

    def analyze(
        self,
        contract: str | Path,
        *,
        mode: str = "defense",
        poc_test: str | None = None,
    ) -> dict[str, Any]:
        resolved_mode = _normalize_mode(mode)
        if resolved_mode == "forensics":
            resolved_mode = "defense"

        contract_path = Path(contract)
        if not contract_path.is_absolute():
            contract_path = (ROOT / contract_path).resolve()

        if resolved_mode == "offense" and not _offense_allowed():
            return self._blocked_offense(contract_path)

        static_slither = self.toolchain.slither_scan(contract_path)
        static_mythril = self.toolchain.mythril_analyze(contract_path)
        fuzz_echidna = ToolResult("echidna", ok=False, skipped=True, skip_reason="needs foundry project dir")
        forge_result = ToolResult("foundry", ok=False, skipped=True, skip_reason="not requested")

        project_dir = contract_path.parent
        if self.toolchain.detect_tools().get("echidna"):
            if (project_dir / "echidna.yaml").is_file() or (project_dir / "foundry.toml").is_file():
                fuzz_echidna = self.toolchain.echidna_fuzz(project_dir)

        allowance = ToolResult("allowance_monitor", ok=False, skipped=True)
        if resolved_mode == "defense":
            allowance = self.toolchain.scan_allowances_hint(os.environ.get("MONITOR_WALLET", "0x0"))

        risks = self._merge_risks(static_slither, static_mythril, fuzz_echidna)

        report: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": resolved_mode,
            "contract": str(contract_path),
            "tools_detected": self.toolchain.detect_tools(),
            "static": {
                "slither": static_slither.to_dict(),
                "mythril": static_mythril.to_dict(),
            },
            "dynamic": {
                "echidna": fuzz_echidna.to_dict(),
            },
            "onchain_monitoring": allowance.to_dict() if allowance.ok else {},
            "risks": risks,
            "risk_count": len(risks),
        }

        if resolved_mode == "offense":
            test_path = poc_test or os.environ.get("DUAL_MODE_POC_TEST", "test/exploit/")
            forge_result = self.toolchain.foundry_exploit_poc(project_dir, test_path)
            report["offense"] = {
                "foundry_poc": forge_result.to_dict(),
                "sandbox": True,
                "note": "PoC runs only under HEXSTRIKE_SANDBOX=1 — local Anvil/Foundry",
            }
        else:
            report["defense"] = {
                "recommendations": self._recommend_fixes(risks),
                "remediation_priority": self._prioritize(risks),
            }

        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.artifact_dir / f"report-{resolved_mode}-{contract_path.stem}.json"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["artifact"] = str(out_path)

        self.bus.publish("skill.dual_mode.complete", report, source="dual_mode_agent")
        return report

    def _merge_risks(self, *results: ToolResult) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        for res in results:
            for f in res.findings:
                merged.append({**f, "source": res.tool})
        return merged

    def _prioritize(self, risks: list[dict[str, Any]]) -> list[str]:
        order = {"High": 0, "high": 0, "Medium": 1, "medium": 1, "Low": 2, "low": 2}
        ranked = sorted(risks, key=lambda r: order.get(str(r.get("severity") or r.get("impact", "")), 3))
        out: list[str] = []
        for r in ranked[:10]:
            title = r.get("title") or r.get("check") or r.get("type") or "finding"
            sev = r.get("severity") or r.get("impact") or "unknown"
            out.append(f"[{sev}] {title} ({r.get('source')})")
        return out

    def _recommend_fixes(self, risks: list[dict[str, Any]]) -> list[str]:
        recs: list[str] = []
        keywords = {
            "reentrancy": "Use checks-effects-interactions and ReentrancyGuard",
            "delegatecall": "Restrict delegatecall targets; prefer transparent proxy patterns",
            "overflow": "Use Solidity 0.8+ checked math or SafeMath",
            "approval": "Revoke stale approvals; use permit with expiry where possible",
            "permit": "Validate EIP-2612 domain separator and nonce replay protection",
        }
        blob = json.dumps(risks).lower()
        for key, fix in keywords.items():
            if key in blob:
                recs.append(fix)
        if not recs:
            recs.append("Review Slither/Mythril output; add unit + fuzz tests before mainnet deploy")
        if self.llm and risks:
            recs.append("LLM available — run llm-handshake for narrative remediation draft")
        return recs

    def _blocked_offense(self, contract_path: Path) -> dict[str, Any]:
        msg = {
            "mode": "offense",
            "blocked": True,
            "reason": "Set HEXSTRIKE_SANDBOX=1 and use local Foundry/Anvil only",
            "contract": str(contract_path),
            "hint": "hexstrike-orchestrator run sandbox-battle",
        }
        self.bus.publish("skill.dual_mode.blocked", msg, source="dual_mode_agent")
        return msg
