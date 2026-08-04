#!/usr/bin/env python3
"""Permit farming analyzer — EIP-2612 / Permit2 / signTypedData abuse."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "forensics"))

from _report_builder import build_attack_chain, finalize_report, load_ioc  # noqa: E402

PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"


def build(ioc: dict) -> dict:
    return {
        "schema": "hexstrike.permit-farming.v1",
        "sample": {
            "name": "EIP-2612 Permit Farming",
            "classification": "offchain_signature_allowance_abuse",
            "standards": ["EIP-2612", "EIP-712", "Permit2"],
            "attack_name": "permit_farming",
        },
        "eip2612_reference": {
            "eip": "https://eips.ethereum.org/EIPS/eip-2612",
            "permit_selector": "0xd505accf",
            "permit2_contract": PERMIT2,
            "wallet_methods": [
                "eth_signTypedData",
                "eth_signTypedData_v4",
                "personal_sign",
            ],
            "typed_data_types": ["Permit", "PermitSingle", "PermitBatch", "PermitTransferFrom"],
        },
        "files_flagged": ioc.get("files_flagged", []),
        "spenders_correlated": ioc.get("spenders_correlated", []),
        "attack_chain": build_attack_chain([
            {"phase": "lure", "detail": "Victim visits phishing dApp mimicking legitimate DeFi UI"},
            {"phase": "typed_data", "detail": "Wallet prompted for EIP-712 Permit signature (not on-chain tx)"},
            {"phase": "allowance", "detail": "Off-chain signature grants spender allowance via permit()"},
            {"phase": "pull", "detail": "Attacker calls transferFrom/permit2 within deadline"},
            {"phase": "impact", "detail": "Full token balance drained without victim sending a transaction"},
        ]),
        "remediation": [
            "Wallet UX: highlight permit spender + unlimited value",
            "Block known malicious spenders at RPC simulation layer",
            "Revoke approvals via revoke.cash / wallet built-ins",
        ],
    }


def main() -> int:
    ioc = load_ioc("permit-farming-eip2612-iocs.json")
    result = finalize_report(
        module="permit",
        instruction_file="permit_farming_forensics.md",
        ioc=ioc,
        report_builder=build,
        bus_source="permit_farming_analyzer",
        out_name="permit-farming-report.json",
        onchain_addresses=ioc.get("spenders_correlated", []),
    )
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
