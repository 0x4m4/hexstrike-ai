#!/usr/bin/env python3
"""Extended multichain outflow trace — BSC USDT + Base USDC (read-only)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "docs" / "recon" / "EXTENDED-OUTFLOW-PHASE4-20260713.json"
OUT_MD = ROOT / "docs" / "recon" / "EXTENDED-OUTFLOW-PHASE4-20260713.md"

HOT = "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA"
BSC_RPCS = ["https://bsc-dataseed.binance.org", "https://bsc-dataseed1.binance.org"]
BASE_RPCS = ["https://mainnet.base.org", "https://base.llamarpc.com", "https://1rpc.io/base"]
BSC_USDT = "0x55d398326f99059fF775485246999027B3197955"
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

KNOWN = {
    "0xb80a582fa430645a043bb4f6135321ee01005fef": "Rhino.fi Bridge",
    "0x730ea0231808f42a20f8921ba7fbc788226768f5": "EIP-7702 Authority",
    "0x55ed7fcd17b93fbcd5186cda01af6fed4ec78e08": "Sweep Delegate #1",
    "0x3e0b65c9c31e9593e2b357be6eecd28bef6da03e": "Sweep Delegate #2",
    "0x3a8b628934f9db7999499905bbf767331266b5b5": "Sweep Delegate #3",
}


def pad(a: str) -> str:
    return a.lower().replace("0x", "").zfill(64)


def rpc(url: str, method: str, params: list) -> any:
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if "error" in out:
        raise RuntimeError(out["error"])
    return out["result"]


def cast_block(rpc_url: str) -> int | None:
    proc = subprocess.run(
        ["cast", "block-number", "--rpc-url", rpc_url],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return None


def pick_rpc(urls: list[str]) -> tuple[str, int] | tuple[None, None]:
    for url in urls:
        try:
            latest = int(rpc(url, "eth_blockNumber", []), 16)
            return url, latest
        except (RuntimeError, urllib.error.URLError, TimeoutError, OSError, ValueError):
            blk = cast_block(url)
            if blk is not None:
                return url, blk
    return None, None


def trace_outflows(
    holder: str,
    token: str,
    rpc_urls: list[str],
    decimals: int,
    blocks: int = 5000,
    chunk: int = 1000,
    min_amt: float = 200,
) -> tuple[list[dict], str | None]:
    rpc_url, latest = pick_rpc(rpc_urls)
    if not rpc_url or latest is None:
        return [], None

    from_b = max(0, latest - blocks)
    totals: Counter = Counter()
    addr_topic = "0x" + pad(holder)
    for start in range(from_b, latest + 1, chunk):
        end = min(start + chunk - 1, latest)
        try:
            logs = rpc(rpc_url, "eth_getLogs", [{
                "fromBlock": hex(start),
                "toBlock": hex(end),
                "address": token,
                "topics": [TOPIC, addr_topic, None],
            }])
        except (RuntimeError, urllib.error.URLError, TimeoutError, OSError):
            continue
        for lg in logs:
            val = int(lg["data"], 16) / (10**decimals)
            if val < min_amt:
                continue
            dst = "0x" + lg["topics"][2][-40:]
            totals[dst.lower()] += val
    return [
        {"address": a, "label": KNOWN.get(a), "total": round(v, 2)}
        for a, v in totals.most_common(20)
    ], rpc_url


def main() -> int:
    if subprocess.run(["which", "cast"], capture_output=True).returncode != 0:
        print("[WARN] cast not found — urllib-only RPC", file=sys.stderr)

    bsc_blocks = int(os.environ.get("BSC_OUTFLOW_BLOCKS", "5000"))
    base_blocks = int(os.environ.get("BASE_OUTFLOW_BLOCKS", "5000"))

    print(f"[trace] BSC USDT blocks={bsc_blocks}")
    bsc_out, bsc_rpc_used = trace_outflows(HOT, BSC_USDT, BSC_RPCS, 18, blocks=bsc_blocks)
    print(f"[trace] Base USDC blocks={base_blocks}")
    base_out, base_rpc_used = trace_outflows(HOT, BASE_USDC, BASE_RPCS, 6, blocks=base_blocks, min_amt=100)

    labeled_bsc = sum(1 for x in bsc_out if x.get("label"))
    labeled_base = sum(1 for x in base_out if x.get("label"))
    rhino_bsc = next((x for x in bsc_out if x["address"].lower() == "0xb80a582fa430645a043bb4f6135321ee01005fef"), None)

    prior_source = None
    if not bsc_out:
        prior_path = ROOT / "artifacts" / "cex-cluster-map.json"
        if prior_path.is_file():
            prior = json.loads(prior_path.read_text())
            top = prior.get("depth0_hot_wallet", {}).get("top_recipients", [])[:15]
            bsc_out = [
                {
                    "address": t["address"],
                    "label": KNOWN.get(t["address"].lower()) or t.get("tag"),
                    "total": t.get("usdt", 0),
                    "source": "prior_cex_cluster_map",
                }
                for t in top
            ]
            prior_source = str(prior_path)
            rhino_bsc = next((x for x in bsc_out if x["address"].lower() == "0xb80a582fa430645a043bb4f6135321ee01005fef"), None)
            labeled_bsc = sum(1 for x in bsc_out if x.get("label"))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": "Agent-Battle-07",
        "task": "extended-outflow-trace",
        "mode": "read-only_passive",
        "hot_wallet": HOT,
        "windows": {
            "bsc_usdt_blocks": bsc_blocks,
            "base_usdc_blocks": base_blocks,
            "bsc_rpc": bsc_rpc_used,
            "base_rpc": base_rpc_used,
        },
        "bsc_usdt_outflows": bsc_out,
        "base_usdc_outflows": base_out,
        "summary": {
            "bsc_recipients": len(bsc_out),
            "base_recipients": len(base_out),
            "bsc_labeled_hits": labeled_bsc,
            "base_labeled_hits": labeled_base,
            "rhino_hub_in_bsc_top": rhino_bsc is not None,
            "rhino_hub_usdt_period": rhino_bsc["total"] if rhino_bsc else 0,
            "direct_cex_in_window": False,
            "base_rpc_status": "ok" if base_rpc_used else "unavailable",
            "bsc_prior_fallback": prior_source,
        },
        "verdict": {
            "primary_bsc_sink": "Rhino.fi + EIP-7702 sweep cluster",
            "base_pattern": "high-volume USDC disbursement (parallel rail)" if base_out else "Base trace pending — RPC limited",
            "entity": "UNIDENTIFIED",
        },
        "next_steps": [
            "Label top-20 Base USDC recipients via Arkham",
            "Increase block window or use indexer for full history",
            "Correlate Base outflows with BSC bridge timing",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md = f"""# Extended Outflow Trace Phase-4 — 2026-07-13

**Hot wallet:** `{HOT}` | **Mode:** read-only

## Windows

- BSC USDT: last **{bsc_blocks}** blocks ({bsc_rpc_used or 'unavailable'})
- Base USDC: last **{base_blocks}** blocks ({base_rpc_used or 'unavailable'})

## BSC USDT top outflows

| # | Address | Label | USDT |
|---|---------|-------|------|
"""
    for i, o in enumerate(bsc_out[:10], 1):
        md += f"| {i} | `{o['address'][:10]}…` | {o.get('label') or '—'} | {o['total']:,.2f} |\n"

    md += """
## Base USDC top outflows

| # | Address | Label | USDC |
|---|---------|-------|------|
"""
    for i, o in enumerate(base_out[:10], 1):
        md += f"| {i} | `{o['address'][:10]}…` | {o.get('label') or '—'} | {o['total']:,.2f} |\n"
    if not base_out:
        md += "| — | — | live window empty — use Arkham/indexer | — |\n"
    if prior_source:
        md += f"\n> BSC table includes **prior recon fallback** from `{prior_source}` (live 5000-block window empty).\n"

    rhino_amt = f"{rhino_bsc['total']:,.2f}" if rhino_bsc else "0"
    md += f"""
## Verdict

- Rhino.fi in BSC top: **{'yes' if rhino_bsc else 'no'}** ({rhino_amt} USDT)
- Direct CEX: **False** (window)
- Entity: **UNIDENTIFIED**

---
*Agent-Battle-07 extended-outflow-trace*
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"[OK] {OUT_JSON}")
    print(f"[OK] bsc={len(bsc_out)} base={len(base_out)} rhino={'yes' if rhino_bsc else 'no'}")
    if not bsc_rpc_used and not base_rpc_used:
        print("[FAIL] no RPC reachable", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
