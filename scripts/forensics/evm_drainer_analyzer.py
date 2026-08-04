#!/usr/bin/env python3
"""EVM drainer kit analyzer — nx_drainer family, multichain sinks, deploy correlation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "forensics"))

from _report_builder import build_attack_chain, finalize_report, load_ioc  # noqa: E402

CHAINS = ["ethereum", "bsc", "polygon", "avalanche", "fantom", "optimism", "arbitrum"]


def build(ioc: dict) -> dict:
    scan = ioc.get("static_scan") or {}
    return {
        "schema": "hexstrike.malware-analysis.v1",
        "repo_path": ioc.get("repo_path"),
        "deploy_repo_path": ioc.get("deploy_repo_path"),
        "sample": {
            **(ioc.get("sample") or {}),
            "family": "nx_drainer",
            "chains_documented": CHAINS,
        },
        "operator_iocs": {
            "github_org": "emmarktech",
            "github_repo": "https://github.com/emmarktech/evm-drainer",
            "related_repos": [
                "https://github.com/emmarktech/evm-drainer",
                "https://github.com/emmarktech/apeterminal-main",
            ],
            "github_repos_found": scan.get("github_repos", []),
        },
        "network_iocs": ioc.get("network_iocs", {}),
        "onchain_iocs": {
            **(ioc.get("onchain_iocs") or {}),
            "sink_addresses": scan.get("addresses", []),
        },
        "deploy_detected": ioc.get("deploy_detected", False),
        "attack_chain": build_attack_chain([
            {"phase": "kit_acquisition", "detail": "Attacker clones emmarktech/evm-drainer + apeterminal deploy kit"},
            {"phase": "deployment", "detail": "Next.js/Vercel or static host serves wallet-connect lure"},
            {"phase": "wallet_connect", "detail": "Victim connects MetaMask/WalletConnect", "walletconnect": scan.get("walletconnect_detected")},
            {"phase": "drain", "detail": "Multichain token sweep to operator sink addresses", "chains": CHAINS},
            {"phase": "cashout", "detail": "Sinks consolidated via bridge/DEX offramps"},
        ]),
        "remediation": [
            "Blocklist sink addresses on monitored chains",
            "Flag WalletConnect sessions to unknown dApp origins",
            "Report GitHub repos for TOS violation",
        ],
    }


def main() -> int:
    ioc = load_ioc("evm-drainer-iocs.json")
    result = finalize_report(
        module="evm",
        instruction_file="evm_drainer_forensics.md",
        ioc=ioc,
        report_builder=build,
        bus_source="evm_drainer_analyzer",
        out_name="evm-drainer-report.json",
        onchain_addresses=(ioc.get("onchain_iocs") or {}).get("addresses", []),
    )
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
