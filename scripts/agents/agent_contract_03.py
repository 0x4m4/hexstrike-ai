#!/usr/bin/env python3
"""Agent-Contract-03 — full EIP-2612 permit farming static analysis."""
from __future__ import annotations

import sys
from pathlib import Path

from forensics_common import emit, merge_scans, output_path, repo_path, scan_tree, utc_now, write_json

SCHEMA = "hexstrike.permit-farming.v1"
PERMIT_SELECTOR = "0xd505accf"
PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"


def main() -> int:
    roots = [
        repo_path("APETERMINAL_REPO", "artifacts/intel/apeterminal-main"),
        repo_path("EVM_DRAINER_REPO", "artifacts/intel/evm-drainer"),
    ]
    flagged: list[str] = []
    spenders: set[str] = set()
    permit_files: list[str] = []

    for root in roots:
        if not root.is_dir():
            continue
        scan = scan_tree(root)
        for rel, hits in (scan.get("flagged_files") or {}).items():
            if "permit" in hits or "walletconnect" in hits:
                flagged.append(str(Path(root.name) / rel))
                permit_files.append(str(root / rel))
        for addr in scan.get("addresses", []):
            spenders.add(addr.lower())

    # Deep read permit-flagged files for spenders
    for pf in permit_files[:50]:
        try:
            text = Path(pf).read_text(encoding="utf-8", errors="ignore")
            for token in text.split():
                if token.startswith("0x") and len(token) == 42:
                    spenders.add(token.lower())
        except OSError:
            pass

    out = output_path("permit-farming-eip2612-iocs.json")
    report = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "sample": {
            "name": "EIP-2612 Permit Farming",
            "classification": "offchain_signature_allowance_abuse",
            "standards": ["EIP-2612", "EIP-712", "Permit2"],
            "attack_name": "permit_farming",
        },
        "eip2612_reference": {
            "eip": "https://eips.ethereum.org/EIPS/eip-2612",
            "permit_selector": PERMIT_SELECTOR,
            "permit2_contract": PERMIT2,
            "wallet_methods": ["eth_signTypedData", "eth_signTypedData_v4", "personal_sign"],
        },
        "files_flagged": flagged,
        "spenders_correlated": sorted(spenders),
    }
    write_json(out, report)
    return emit({
        "success": True,
        "agent": "Agent-Contract-03",
        "task": "permit-farming-analyze",
        "output": str(out),
        "classification": "offchain_signature_allowance_abuse",
        "files_flagged": len(flagged),
        "spenders_correlated": len(spenders),
    })


if __name__ == "__main__":
    sys.exit(main())
