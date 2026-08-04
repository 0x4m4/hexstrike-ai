#!/usr/bin/env python3
"""Solana drainer analyzer — trojanized kit, C2 correlation with TRX family."""
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
        "sample": {
            **(ioc.get("sample") or {}),
            "github": "https://github.com/brian4903/Solana-Drainer-Tool",
            "blockchain": "solana",
        },
        "network_iocs": ioc.get("network_iocs", {}),
        "onchain_iocs": {
            "program_ids": scan.get("solana_addresses", []),
            "sink_addresses": scan.get("addresses", []),
        },
        "cross_family_correlation": {
            "shared_c2_pattern": "api.nailproxy.space",
            "related_trojan": "TRX-Drainer-Tool",
            "c2_match": c2 == "api.nailproxy.space" if c2 else None,
        },
        "attack_chain": build_attack_chain([
            {"phase": "delivery", "detail": "Fake Solana drainer GitHub repo"},
            {"phase": "loader", "detail": "Windows x64 trojan masquerading as build toolchain"},
            {"phase": "c2", "detail": f"Exfil to {c2 or 'unknown C2'}", "host": c2},
            {"phase": "impact", "detail": "Solana key material theft"},
        ]),
    }


def main() -> int:
    ioc = load_ioc("solana-drainer-tool-iocs.json")
    result = finalize_report(
        module="solana",
        instruction_file="solana_drainer_forensics.md",
        ioc=ioc,
        report_builder=build,
        bus_source="solana_drainer_analyzer",
        out_name="solana-drainer-report.json",
        network_hosts=(ioc.get("network_iocs") or {}).get("hosts", []),
    )
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
