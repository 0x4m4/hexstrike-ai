#!/usr/bin/env python3
"""Read-only multichain recon — per-target RPC by chain_id (BSC + Base)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = Path(__file__).resolve().parent
PROFILES = ROOT / "artifacts" / "sandbox" / "target-profiles.json"
BUNDLE = ROOT / "artifacts" / "sandbox" / "target-recon-bundle.json"
MULTI_BUNDLE = ROOT / "artifacts" / "sandbox" / "multichain-recon-bundle.json"

CHAIN_RPC = {
    56: os.environ.get("BSC_RPC", "https://bsc-dataseed.binance.org"),
    8453: os.environ.get("BASE_RPC", "https://mainnet.base.org"),
}
BSC_FALLBACK = os.environ.get("BSC_RPC_FALLBACK", "https://bsc-dataseed1.binance.org")

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def cast_val(args: list[str]) -> str:
    proc = subprocess.run(["cast", *args], capture_output=True, text=True, check=False)
    return (proc.stdout or proc.stderr or "").strip() if proc.returncode == 0 else "ERROR"


def wei_to_eth(wei: str) -> str:
    try:
        return f"{int(wei) / 10**18:.6f}"
    except (ValueError, TypeError):
        return "?"


def token_balance(token: str, holder: str, rpc: str, decimals: int) -> float | None:
    for url in (rpc, BSC_FALLBACK if rpc == CHAIN_RPC[56] else None):
        if not url:
            continue
        raw = cast_val(["call", token, "balanceOf(address)(uint256)", holder, "--rpc-url", url])
        if raw in ("ERROR", ""):
            continue
        try:
            val_str = raw.split()[0].strip("[]")
            if "e" in val_str.lower() or "E" in val_str:
                return float(val_str) / (10**decimals)
            return int(val_str) / (10**decimals)
        except (ValueError, IndexError):
            continue
    return None


def recon_wallet(address: str, rpc: str, chain_id: int, source: str) -> dict:
    bal = cast_val(["balance", address, "--rpc-url", rpc])
    nonce = cast_val(["nonce", address, "--rpc-url", rpc])
    code = cast_val(["code", address, "--rpc-url", rpc])
    chain = cast_val(["chain-id", "--rpc-url", rpc])
    return {
        "source": source,
        "rpc": rpc,
        "chain_id": chain_id,
        "address": address,
        "balance_wei": bal,
        "balance_eth": wei_to_eth(bal),
        "nonce": nonce,
        "is_contract": code not in ("0x", "ERROR", ""),
        "chain_id_live": chain,
        "reachable": bal != "ERROR" and nonce != "ERROR",
    }


def pad_addr(addr: str) -> str:
    return addr.lower().replace("0x", "").zfill(64)


def rpc_get_logs(rpc: str, payload: dict) -> list:
    body = json.dumps({"jsonrpc": "2.0", "method": "eth_getLogs", "params": [payload], "id": 1}).encode()
    req = urllib.request.Request(rpc, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read().decode())
        if out.get("error"):
            return []
        return out.get("result") or []
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []


def sample_outflows(address: str, token: str, rpc: str, decimals: int, blocks: int = 2000, min_amt: float = 100) -> list[dict]:
    latest_raw = cast_val(["block-number", "--rpc-url", rpc])
    if latest_raw == "ERROR":
        return []
    latest = int(latest_raw)
    from_b = max(0, latest - blocks)
    addr_topic = "0x" + pad_addr(address)
    logs = rpc_get_logs(rpc, {
        "fromBlock": hex(from_b),
        "toBlock": hex(latest),
        "address": token,
        "topics": [TRANSFER_TOPIC, addr_topic, None],
    })
    totals: dict[str, float] = {}
    for lg in logs:
        try:
            val = int(lg["data"], 16) / (10**decimals)
        except (ValueError, KeyError):
            continue
        if val < min_amt:
            continue
        dst = "0x" + lg["topics"][2][-40:]
        totals[dst.lower()] = totals.get(dst.lower(), 0) + val
    return [
        {"address": a, "total": round(v, 2)}
        for a, v in sorted(totals.items(), key=lambda x: -x[1])[:10]
    ]


def _wallet_verdict(wallet: dict, live: dict, token_bal: float | None) -> dict:
    role = wallet.get("role", "unknown")
    nonce_i = int(live.get("nonce", 0)) if str(live.get("nonce", "0")).isdigit() else 0
    reachable = live.get("reachable", False)
    risk = "low"
    findings: list[str] = []

    if not reachable:
        return {"status": "UNREACHABLE", "risk_level": "unknown", "findings": ["RPC failed"], "recommended_action": "Retry alternate RPC"}

    if role == "hot_wallet_bsc":
        risk = "high"
        findings.append(f"BSC USDT treasury nonce={nonce_i}")
        if token_bal:
            findings.append(f"USDT balance={token_bal:,.2f}")
    elif role == "hot_wallet_base":
        risk = "high"
        findings.append(f"Base USDC parallel rail nonce={nonce_i}")
        if token_bal:
            findings.append(f"USDC balance={token_bal:,.2f}")
    elif role == "rhino_hub_bsc":
        risk = "medium"
        findings.append("Rhino.fi bridge sink — cross-chain exit")
        if token_bal:
            findings.append(f"Hub USDT float={token_bal:,.2f}")
    elif role == "sweep_router_primary":
        findings.append("EIP-7702 sweep delegate — pass-through")
    elif role == "eip7702_implementation":
        findings.append("Shared signature-gated payment impl")

    status = "ACTIVE" if nonce_i > 0 or live.get("is_contract") else "QUIET"
    actions = {
        "hot_wallet_bsc": "Monitor BSC USDT outflows + sweep delegates",
        "hot_wallet_base": "Trace Base USDC outflows — correlate with Rhino bridge",
        "rhino_hub_bsc": "Cross-chain exit monitoring — bridge events",
    }
    return {
        "status": status,
        "risk_level": risk,
        "findings": findings,
        "recommended_action": actions.get(role, "Continue read-only multichain tracing"),
    }


def _bundle_summary(results: list[dict]) -> dict:
    high = [r for r in results if r.get("verdict", {}).get("risk_level") == "high"]
    medium = [r for r in results if r.get("verdict", {}).get("risk_level") == "medium"]
    active = [r for r in results if r.get("verdict", {}).get("status") == "ACTIVE"]
    return {
        "headline": f"{len(results)} multichain targets — {len(active)} active, {len(high)} high-risk",
        "high_risk_roles": [r["role"] for r in high],
        "medium_risk_roles": [r["role"] for r in medium],
        "active_count": len(active),
    }


def main() -> int:
    if not PROFILES.is_file():
        print("[FAIL] run generate-target-profile first", file=sys.stderr)
        return 1
    if not subprocess.run(["which", "cast"], capture_output=True).returncode == 0:
        print("[FAIL] cast not found", file=sys.stderr)
        return 1

    catalog = json.loads(PROFILES.read_text(encoding="utf-8"))
    results: list[dict] = []

    for w in catalog.get("wallets", []):
        addr = w["address"]
        role = w["role"]
        chain_id = int(w.get("chain_id", 56))
        rpc = CHAIN_RPC.get(chain_id)
        if not rpc:
            print(f"[SKIP] {role} unknown chain_id={chain_id}")
            continue

        ctx = w.get("context", {})
        token = ctx.get("token_contract")
        decimals = int(ctx.get("token_decimals", 18))

        print(f"=== {role} {addr} chain={chain_id} ===")
        live = recon_wallet(addr, rpc, chain_id, f"live_chain_{chain_id}")
        token_bal = token_balance(token, addr, rpc, decimals) if token else None
        outflows = []
        if token and role.startswith("hot_wallet"):
            outflows = sample_outflows(addr, token, rpc, decimals)
        if token:
            tb = f"{token_bal:,.2f}" if token_bal is not None else "?"
            extra = f" outflows_sampled={len(outflows)}" if outflows is not None else ""
            print(f"  token={tb}{extra}")

        print(f"  bal={live['balance_eth']} ETH nonce={live['nonce']} contract={live['is_contract']}")

        results.append({
            "role": role,
            "address": addr,
            "chain": w.get("chain"),
            "chain_id": chain_id,
            "priority": w.get("priority"),
            "context": ctx,
            "live": live,
            "token_balance": token_bal,
            "recent_outflows": outflows,
            "verdict": _wallet_verdict(w, live, token_bal),
        })

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "multichain_read_only",
        "wallet_count": len(results),
        "chains": list(CHAIN_RPC.keys()),
        "wallets": results,
        "summary": _bundle_summary(results),
    }

    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    MULTI_BUNDLE.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")

    print(f"\n[OK] bundle: {BUNDLE}")
    print(f"[OK] {bundle['summary']['headline']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
