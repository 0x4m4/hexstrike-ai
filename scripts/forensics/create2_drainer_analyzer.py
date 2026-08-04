#!/usr/bin/env python3
"""CREATE2 drainer analyzer — EIP-1014 / EIP-1167 factory rotation pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "forensics"))

from _report_builder import build_attack_chain, finalize_report, load_ioc  # noqa: E402


def build(ioc: dict) -> dict:
    claims = ioc.get("claim_contracts_correlated", [])
    return {
        "schema": "hexstrike.create2-drainer.v1",
        "sample": {
            "name": "CREATE2 Drainer Evasion",
            "classification": "deterministic_contract_deployment_abuse",
            "standards": ["EIP-1014", "EIP-1167"],
            "attack_name": "create2_factory_rotation",
        },
        "eip1014_reference": {
            "eip": "https://eips.ethereum.org/EIPS/eip-1014",
            "opcode": "0xf5",
            "address_formula": "keccak256(0xff ++ deployer ++ salt ++ keccak256(init_code))[12:]",
            "drainer_ttp": [
                "Deploy fresh claim/drain contract per phishing domain",
                "Evade static blocklists that target fixed addresses",
                "Salt grinding for vanity or cross-chain address reuse",
                "Minimal proxy (EIP-1167) + CREATE2 factory pipelines",
            ],
        },
        "files_flagged": ioc.get("files_flagged", []),
        "claim_contracts_correlated": claims,
        "attack_chain": build_attack_chain([
            {"phase": "factory_deploy", "detail": "Attacker deploys CREATE2 factory (immutable deployer)"},
            {"phase": "salt_grind", "detail": "Optional vanity salt for cross-chain address reuse"},
            {"phase": "minimal_proxy", "detail": "EIP-1167 clone points to shared drain implementation"},
            {"phase": "phishing_bind", "detail": "Each domain uses deterministic but unique contract address"},
            {"phase": "drain", "detail": "Victim approves/interacts with un-blocklisted fresh address"},
            {"phase": "rotate", "detail": "New salt+domain after blocklist — static IOC decay"},
        ]),
        "blocklist_evasion": {
            "technique": "ephemeral_contract_addresses",
            "detection": "Monitor factory deployer + init_code hash, not just sink",
        },
    }


def main() -> int:
    ioc = load_ioc("create2-drainer-iocs.json")
    addrs = list(ioc.get("claim_contracts_correlated", []))
    # Also pull claim contract from intel scan if present
    for f in ioc.get("files_flagged", []):
        if "claim" in str(f).lower():
            pass
    result = finalize_report(
        module="create2",
        instruction_file="create2_drainer_forensics.md",
        ioc=ioc,
        report_builder=build,
        bus_source="create2_drainer_analyzer",
        out_name="create2-drainer-report.json",
        onchain_addresses=addrs,
    )
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
