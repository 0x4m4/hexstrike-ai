#!/usr/bin/env python3
"""Agent-Contract-04 — full CREATE2 / EIP-1167 factory pipeline analysis."""
from __future__ import annotations

import sys
from pathlib import Path

from forensics_common import emit, output_path, repo_path, scan_tree, utc_now, write_json

SCHEMA = "hexstrike.create2-drainer.v1"


def main() -> int:
    scan_roots_env = __import__("os").environ.get("CREATE2_SCAN_ROOTS")
    if scan_roots_env:
        roots = [Path(p.strip()) for p in scan_roots_env.split(":")]
    else:
        roots = [
            repo_path("APETERMINAL_REPO", "artifacts/intel/apeterminal-main"),
            repo_path("EVM_DRAINER_REPO", "artifacts/intel/evm-drainer"),
        ]

    flagged: list[str] = []
    claim_contracts: set[str] = set()

    for root in roots:
        if not root.is_dir():
            continue
        scan = scan_tree(root)
        for rel, hits in (scan.get("flagged_files") or {}).items():
            if "create2" in hits:
                flagged.append(str(root / rel))
        for path_str in flagged[-20:]:
            try:
                text = Path(path_str).read_text(encoding="utf-8", errors="ignore")
                if "claim" in text.lower():
                    for token in text.split():
                        if token.startswith("0x") and len(token) == 42:
                            claim_contracts.add(token.lower())
            except OSError:
                pass
        for addr in scan.get("addresses", []):
            if "claim" in str(scan.get("flagged_files", {})).lower():
                claim_contracts.add(addr.lower())

    out = output_path("create2-drainer-iocs.json")
    report = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
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
        "files_flagged": flagged,
        "claim_contracts_correlated": sorted(claim_contracts),
    }
    write_json(out, report)
    return emit({
        "success": True,
        "agent": "Agent-Contract-04",
        "task": "create2-analyze",
        "output": str(out),
        "classification": "deterministic_contract_deployment_abuse",
        "files_flagged": len(flagged),
        "claim_contracts_correlated": len(claim_contracts),
    })


if __name__ == "__main__":
    sys.exit(main())
