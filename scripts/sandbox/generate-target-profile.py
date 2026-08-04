#!/usr/bin/env python3
"""Build multi-wallet target profiles from HexStrike recon artifacts."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = Path(__file__).resolve().parent
sys.path.insert(0, str(SANDBOX))

from wallet_registry import load_wallet_catalog  # noqa: E402

OUT_DIR = ROOT / "artifacts" / "sandbox"
PROFILES_JSON = OUT_DIR / "target-profiles.json"
PROFILE_JSON = OUT_DIR / "target-profile.json"
REGISTRY_JSON = OUT_DIR / "wallets.registry.json"


def main() -> int:
    wallets = load_wallet_catalog()
    if not wallets:
        print("[FAIL] no wallets in catalog", file=sys.stderr)
        return 1

    primary = wallets[0]
    entity = json.loads((ROOT / "artifacts" / "entity-id.json").read_text(encoding="utf-8")) if (ROOT / "artifacts" / "entity-id.json").is_file() else {}
    graph_path = ROOT / "artifacts" / "hot-wallet-onchain-graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8")) if graph_path.is_file() else {}

    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only_recon",
        "scope": "authorized_defensive_research",
        "wallet_count": len(wallets),
        "wallets": [w.to_dict() for w in wallets],
        "rpc_endpoints": {
            "bsc_public": "https://bsc-dataseed.binance.org",
            "bsc_fallback": "https://bsc-dataseed1.binance.org",
            "base_public": "https://mainnet.base.org",
            "local_fork": "http://127.0.0.1:8545",
        },
        "constraints": [
            "no_remote_exploit",
            "no_balance_drain",
            "no_unsigned_mainnet_tx",
            "read-only unless operator owns keys",
        ],
    }

    # Back-compat single profile (primary hot wallet)
    legacy = {
        "generated_at": catalog["generated_at"],
        "mode": catalog["mode"],
        "scope": catalog["scope"],
        "primary_target": {
            "role": primary.role,
            "address": primary.address,
            "chain": primary.chain,
            "chain_id": primary.chain_id,
            "labels": entity.get("methods", {}).get("bscan_labels", {}),
            "graph_summary": {
                "usdt_out_txs": graph.get("usdt_out_txs"),
                "net_usdt_period": graph.get("net_usdt_period"),
                "top_destinations": (graph.get("top_destinations") or [])[:5],
            },
        },
        "related_targets": {w.role: w.address for w in wallets[1:6]},
        "rpc_endpoints": catalog["rpc_endpoints"],
        "constraints": catalog["constraints"],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_JSON.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    PROFILE_JSON.write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")
    REGISTRY_JSON.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    print(f"[OK] wrote {PROFILES_JSON} ({len(wallets)} wallets)")
    print(f"[OK] wrote {PROFILE_JSON} (primary={primary.address})")
    for w in wallets[:6]:
        print(f"     • {w.role:20} {w.address}")
    if len(wallets) > 6:
        print(f"     … +{len(wallets) - 6} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
