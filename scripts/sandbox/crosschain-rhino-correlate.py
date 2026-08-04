#!/usr/bin/env python3
"""Cross-chain correlation: BSC Rhino hub ↔ Base USDC hot wallet treasury."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "recon"
BUNDLE = ROOT / "artifacts" / "sandbox" / "multichain-recon-bundle.json"
PHASE2 = DOCS / "SWEEP-PHASE2-AUDIT-20260713.json"
OUT_JSON = DOCS / "CROSSCHAIN-PHASE3-20260713.json"
OUT_MD = DOCS / "CROSSCHAIN-PHASE3-20260713.md"

HOT = "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA"
RHINO = "0xb80a582fa430645a043bb4f6135321ee01005fef"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def wallet_by_role(bundle: dict, role: str) -> dict | None:
    for w in bundle.get("wallets", []):
        if w.get("role") == role:
            return w
    return None


def fmt_amt(val: float | None, default: str = "N/A") -> str:
    return f"{val:,.2f}" if val is not None else default


def main() -> int:
    bundle = load(BUNDLE)
    if not bundle.get("wallets"):
        print("[FAIL] multichain-recon-bundle.json missing — run multichain-target-recon first", file=sys.stderr)
        return 1

    phase2 = load(PHASE2)
    hot_bsc = wallet_by_role(bundle, "hot_wallet_bsc")
    hot_base = wallet_by_role(bundle, "hot_wallet_base")
    rhino = wallet_by_role(bundle, "rhino_hub_bsc")

    bsc_usdt = hot_bsc.get("token_balance") if hot_bsc else None
    base_usdc = hot_base.get("token_balance") if hot_base else None
    hub_usdt = rhino.get("token_balance") if rhino else None
    total_usd = (bsc_usdt or 0) + (base_usdc or 0)

    base_out = hot_base.get("recent_outflows", []) if hot_base else []
    bsc_out = hot_bsc.get("recent_outflows", []) if hot_bsc else []

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only_passive",
        "phase": "crosschain-phase-3",
        "hot_wallet": HOT,
        "live_balances": {
            "bsc_usdt": bsc_usdt,
            "base_usdc": base_usdc,
            "combined_stable_usd": round(total_usd, 2),
            "rhino_hub_usdt_float": hub_usdt,
        },
        "activity": {
            "bsc_nonce": hot_bsc.get("live", {}).get("nonce") if hot_bsc else None,
            "base_nonce": hot_base.get("live", {}).get("nonce") if hot_base else None,
            "base_more_active": int(hot_base.get("live", {}).get("nonce", 0) or 0) > int(hot_bsc.get("live", {}).get("nonce", 0) or 0) if hot_bsc and hot_base else None,
        },
        "correlation": {
            "rhino_hub_role": "BSC cross-chain exit sink",
            "sweep_rail": phase2.get("architecture_confirmed", {}),
            "base_parallel_treasury": True,
            "direct_cex_from_either_chain": False,
            "hypothesis": "BSC USDT payroll → sweep/EIP-7702 → Rhino hub; Base USDC is parallel treasury rail",
            "confidence": "medium",
        },
        "recent_outflows_sample": {
            "base_usdc_top": base_out[:5],
            "bsc_usdt_top": bsc_out[:5],
        },
        "architecture": {
            "bsc_rail": f"hot → 4x EIP-7702 delegates → impl → Rhino hub ({RHINO})",
            "base_rail": f"hot ({HOT}) holds USDC on Base — independent high-activity EOA",
            "multichain_total_usd": round(total_usd, 2),
        },
        "vectors_closed": [
            "Single-chain-only analysis",
            "Direct hot→CEX on Base (sample window)",
            "Direct hot→CEX on BSC (prior depth-2)",
        ],
        "vectors_open": [
            "Entity UNIDENTIFIED",
            "Base USDC top recipients labeling",
            "Rhino bridge destination chain mapping",
        ],
        "next_steps": [
            "Arkham multichain cluster labels",
            "Extended Base USDC outflow window (Basescan Pro / indexer)",
            "Rhino.fi bridge event correlation BSC→Base",
            "Monitor hot wallet delegate deployments",
        ],
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md = f"""# Cross-Chain Phase-3 — 2026-07-13

**Workflow:** `field-targets-7` | **Mode:** read-only multichain

## Live Balances

| Chain | Token | Balance |
|-------|-------|---------|
| BSC | USDT | **{fmt_amt(bsc_usdt)}** |
| Base | USDC | **{fmt_amt(base_usdc)}** |
| **Combined** | — | **${fmt_amt(total_usd if total_usd else None)}** |
| Rhino hub (BSC) | USDT float | {fmt_amt(hub_usdt)} |

## Activity

| Chain | Nonce |
|-------|-------|
| BSC | {hot_bsc.get('live', {}).get('nonce') if hot_bsc else '?'} |
| Base | **{hot_base.get('live', {}).get('nonce') if hot_base else '?'}** |

Base nonce significantly higher — parallel high-activity treasury rail.

## Architecture

```
BSC:  hot → EIP-7702 sweeps → impl → Rhino hub → cross-chain
Base: hot → USDC treasury (parallel rail, ~{fmt_amt(base_usdc)} USDC)
```

## Correlation verdict

- Rhino.fi hub = BSC exit sink (confirmed Phase-2)
- Base USDC = parallel treasury, **not** direct CEX in sample window
- Entity: **UNIDENTIFIED**
- Combined stable exposure: **${fmt_amt(total_usd if total_usd else None)}**

## Base USDC top outflows (sample)

"""
    for o in base_out[:5]:
        md += f"- `{o['address'][:10]}…` — {o['total']:,.2f} USDC\n"

    md += """
## Next steps

1. Arkham multichain labels
2. Extended Base outflow trace
3. Rhino bridge BSC→Base event correlation

---
*Orchestrator agents: OSINT-03 + Battle-07 + Report-06*
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"[OK] {OUT_JSON}")
    print(f"[OK] combined=${total_usd:,.2f} base_nonce={hot_base.get('live', {}).get('nonce') if hot_base else '?'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
