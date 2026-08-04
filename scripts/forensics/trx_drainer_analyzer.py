#!/usr/bin/env python3
"""TRX Drainer static IOC analyzer — full report with attack_chain + on-chain."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "forensics"))

from _report_builder import build_attack_chain, finalize_report, load_ioc  # noqa: E402


def build(ioc: dict) -> dict:
    scan = ioc.get("static_scan") or {}
    c2 = (ioc.get("network_iocs") or {}).get("c2_host")
    return {
        "schema": "hexstrike.malware-analysis.v1",
        "repo_path": ioc.get("repo_path"),
        "sample": ioc.get("sample", {}),
        "network_iocs": {
            **(ioc.get("network_iocs") or {}),
            "urls": scan.get("urls", [])[:20],
            "telegram_handles": scan.get("telegram_handles", []),
            "discord_webhooks": scan.get("discord_webhooks", []),
        },
        "onchain_iocs": ioc.get("onchain_iocs", {}),
        "loader_analysis": {
            "loader_paths": scan.get("loader_paths", []),
            "platform": ioc.get("sample", {}).get("loader_platform"),
            "files_analyzed": scan.get("files_analyzed", 0),
        },
        "attack_chain": build_attack_chain([
            {"phase": "delivery", "detail": "Trojanized fake TRX drainer distributed as open-source kit"},
            {"phase": "social_engineering", "detail": "Victim believes they run a legitimate drainer PoC"},
            {"phase": "loader", "detail": "Windows x64 loader exfiltrates wallet material", "artifacts": scan.get("loader_paths", [])[:5]},
            {"phase": "c2_exfil", "detail": f"Data sent to C2 host {c2 or 'unknown'}", "host": c2},
            {"phase": "impact", "detail": "Private keys / seed phrases stolen — not on-chain drain from victim EOA directly"},
        ]),
        "remediation": [
            "Block C2 domains at DNS/firewall",
            "Hunt for api.nailproxy.space connections in endpoint logs",
            "Do not execute unknown drainer kits on operator workstations",
        ],
    }


def main() -> int:
    ioc = load_ioc("trx-drainer-tool-iocs.json")
    result = finalize_report(
        module="trx",
        instruction_file="trx_drainer_forensics.md",
        ioc=ioc,
        report_builder=build,
        bus_source="trx_drainer_analyzer",
        out_name="trx-drainer-report.json",
        network_hosts=(ioc.get("network_iocs") or {}).get("hosts", []),
        onchain_addresses=(ioc.get("onchain_iocs") or {}).get("addresses", []),
    )
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
