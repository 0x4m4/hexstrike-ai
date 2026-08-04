#!/usr/bin/env python3
"""Vanilla Drainer OSINT analyzer — DaaS fee wallet + on-chain depth."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "forensics"))

from _report_builder import build_attack_chain, finalize_report, load_ioc  # noqa: E402

FEE_WALLET = "0x9d38606c16e6c4f7b1ed4224ea5724ff5c6e710d"


def build(ioc: dict) -> dict:
    return {
        "schema": "hexstrike.malware-analysis.v1",
        "sample": {
            **(ioc.get("sample") or {}),
            "active_since": "2024-10",
            "commission_pct": "15-20",
            "evasion": [
                "rotating_phishing_domains",
                "fresh_malicious_contract_per_site",
                "blockaid_bypass_claimed_in_ads",
            ],
            "predecessor_customers": ["Inferno Drainer", "Angel Drainer"],
        },
        "osint_sources": [
            "Darkbit (Cointelegraph Aug 2025)",
            "Telegram private SaaS channels",
            "Victim wallet permit/approval traces",
        ],
        "onchain_iocs": ioc.get("onchain_iocs", {}),
        "osint_intel": ioc.get("osint_intel", {}),
        "attack_chain": build_attack_chain([
            {"phase": "operator_onboarding", "detail": "Affiliate joins Vanilla DaaS via Telegram"},
            {"phase": "site_spinup", "detail": "Fresh phishing domain + unique malicious contract per site"},
            {"phase": "lure", "detail": "Airdrop/claim/mint UX with Blockaid evasion claims"},
            {"phase": "drain", "detail": "Victim approves token spend or signs permit"},
            {"phase": "fee_split", "detail": f"15-20% commission to fee wallet {FEE_WALLET}"},
        ]),
    }


def main() -> int:
    ioc = load_ioc("vanilla-drainer-iocs.json")
    result = finalize_report(
        module="vanilla",
        instruction_file="vanilla_drainer_forensics.md",
        ioc=ioc,
        report_builder=build,
        bus_source="vanilla_drainer_analyzer",
        out_name="vanilla-drainer-report.json",
        onchain_addresses=[FEE_WALLET],
    )
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
