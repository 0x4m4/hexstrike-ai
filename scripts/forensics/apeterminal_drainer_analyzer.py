#!/usr/bin/env python3
"""ApeTerminal drainer analyzer — friend.tech impersonation, Next.js deploy surface."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "forensics"))

from _report_builder import build_attack_chain, finalize_report, load_ioc  # noqa: E402


def build(ioc: dict) -> dict:
    scan = ioc.get("static_scan") or {}
    return {
        "schema": "hexstrike.malware-analysis.v1",
        "repo_path": ioc.get("repo_path"),
        "sample": {
            **(ioc.get("sample") or {}),
            "family": "nx_drainer_apeterminal",
            "chains": ["ethereum-mainnet", "bsc"],
            "impersonation": "friend.tech",
        },
        "operator_iocs": ioc.get("operator_iocs", {}),
        "network_iocs": ioc.get("network_iocs", {}),
        "onchain_iocs": ioc.get("onchain_iocs", {}),
        "frontend_surface": {
            "framework": "nextjs",
            "deploy_target": "vercel",
            "flagged_files": list((scan.get("flagged_files") or {}).keys())[:20],
        },
        "attack_chain": build_attack_chain([
            {"phase": "brand_abuse", "detail": "Clone friend.tech UX to lower victim suspicion"},
            {"phase": "hosting", "detail": "Deploy on Vercel/custom domain with short TTL"},
            {"phase": "connect", "detail": "WalletConnect / injected provider hook"},
            {"phase": "approve_drain", "detail": "Unlimited ERC20 approvals + native sweep"},
            {"phase": "rotate", "detail": "Operator rotates domain + sink after blocklist"},
        ]),
    }


def main() -> int:
    ioc = load_ioc("apeterminal-main-iocs.json")
    result = finalize_report(
        module="apeterminal",
        instruction_file="apeterminal_forensics.md",
        ioc=ioc,
        report_builder=build,
        bus_source="apeterminal_drainer_analyzer",
        out_name="apeterminal-drainer-report.json",
        onchain_addresses=(ioc.get("onchain_iocs") or {}).get("addresses", []),
    )
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
