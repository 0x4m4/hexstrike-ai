#!/usr/bin/env python3
"""Read-only on-chain recon for all wallets in target-profiles.json."""
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
sys.path.insert(0, str(SANDBOX))

PROFILES = ROOT / "artifacts" / "sandbox" / "target-profiles.json"
BUNDLE = ROOT / "artifacts" / "sandbox" / "target-recon-bundle.json"
LEGACY = ROOT / "artifacts" / "sandbox" / "target-recon-report.json"


def rpc_ok(url: str) -> bool:
    payload = json.dumps({"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            json.loads(resp.read().decode())
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False


def cast_val(args: list[str]) -> str:
    proc = subprocess.run(["cast", *args], capture_output=True, text=True, check=False)
    out = (proc.stdout or proc.stderr or "").strip()
    return out if proc.returncode == 0 else "ERROR"


def wei_to_eth(wei: str) -> str:
    try:
        v = int(wei)
        return f"{v / 10**18:.6f}"
    except (ValueError, TypeError):
        return "?"


def recon_wallet(address: str, rpc: str, source: str) -> dict:
    bal = cast_val(["balance", address, "--rpc-url", rpc])
    nonce = cast_val(["nonce", address, "--rpc-url", rpc])
    code = cast_val(["code", address, "--rpc-url", rpc])
    chain = cast_val(["chain-id", "--rpc-url", rpc])
    is_contract = code not in ("0x", "ERROR", "")
    return {
        "source": source,
        "rpc": rpc,
        "address": address,
        "balance_wei": bal,
        "balance_eth": wei_to_eth(bal),
        "nonce": nonce,
        "is_contract": is_contract,
        "chain_id": chain,
        "reachable": bal != "ERROR" and nonce != "ERROR",
    }


def simulate_fork_trigger(address: str, fork_rpc: str) -> dict:
    low = "0x" + hex(300_000_000_000_000_000)[2:]
    high = "0x56BC75E2D63100000"
    subprocess.run(["cast", "rpc", "anvil_setBalance", address, low, "--rpc-url", fork_rpc],
                   capture_output=True, check=False)
    bot = subprocess.run(
        [sys.executable, str(SANDBOX / "dummy_bot.py"), "--once", "--dry-run"],
        cwd=str(ROOT),
        env={**os.environ, "BOT_ADDRESS": address, "RPC_URL": fork_rpc, "DRY_RUN": "true",
             "HARDENING_ENABLED": "true", "DIRECT_RPC_URL": fork_rpc},
        capture_output=True, text=True, check=False,
    )
    subprocess.run(["cast", "rpc", "anvil_setBalance", address, high, "--rpc-url", fork_rpc],
                   capture_output=True, check=False)
    return {
        "simulated": True,
        "dry_run_poll_exit": bot.returncode,
        "note": "fork-only anvil_setBalance low-balance simulation",
    }


def main() -> int:
    if not PROFILES.is_file():
        print("[FAIL] run generate-target-profile.py first", file=sys.stderr)
        return 1
    if not shutil_which("cast"):
        print("[FAIL] cast not found", file=sys.stderr)
        return 1

    catalog = json.loads(PROFILES.read_text(encoding="utf-8"))
    bsc_rpc = catalog.get("rpc_endpoints", {}).get("bsc_public", "https://bsc-dataseed.binance.org")
    fork_rpc = os.environ.get("RPC_URL", catalog.get("rpc_endpoints", {}).get("local_fork", "http://127.0.0.1:8545"))
    fork_up = rpc_ok(fork_rpc) and cast_val(["chain-id", "--rpc-url", fork_rpc]) == "56"

    results: list[dict] = []
    for w in catalog.get("wallets", []):
        addr = w["address"]
        role = w["role"]
        print(f"=== {role} {addr} ===")
        live = recon_wallet(addr, bsc_rpc, "bsc_live")
        print(f"  [live] bal={live['balance_eth']} ETH nonce={live['nonce']} contract={live['is_contract']}")

        entry = {
            "role": role,
            "address": addr,
            "priority": w.get("priority"),
            "context": w.get("context", {}),
            "live": live,
            "fork": None,
            "fork_simulation": None,
            "verdict": _wallet_verdict(w, live),
        }

        if fork_up:
            fork = recon_wallet(addr, fork_rpc, "local_fork")
            print(f"  [fork] bal={fork['balance_eth']} ETH nonce={fork['nonce']}")
            entry["fork"] = fork
            if role in ("hot_wallet", "authority", "operator_local"):
                entry["fork_simulation"] = simulate_fork_trigger(addr, fork_rpc)

        results.append(entry)

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "multi_wallet_read_only",
        "wallet_count": len(results),
        "bsc_rpc": bsc_rpc,
        "fork_rpc": fork_rpc if fork_up else None,
        "fork_active": fork_up,
        "wallets": results,
        "summary": _bundle_summary(results),
    }

    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")

    # Legacy single-wallet report (primary only)
    primary = results[0] if results else {}
    LEGACY.write_text(json.dumps({
        "generated_at": bundle["generated_at"],
        "target": primary.get("address"),
        "checks": [c for c in [primary.get("live"), primary.get("fork")] if c],
        "verdict": primary.get("verdict"),
    }, indent=2) + "\n", encoding="utf-8")

    print(f"\n[OK] bundle: {BUNDLE}")
    print(f"[OK] summary: {bundle['summary']['headline']}")
    return 0


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def _wallet_verdict(wallet: dict, live: dict) -> dict:
    role = wallet.get("role", "unknown")
    reachable = live.get("reachable", False)
    is_contract = live.get("is_contract", False)
    nonce = live.get("nonce", "0")
    try:
        nonce_i = int(nonce) if str(nonce).isdigit() else 0
    except ValueError:
        nonce_i = 0

    risk = "low"
    findings: list[str] = []
    if not reachable:
        risk = "unknown"
        findings.append("RPC read failed")
    elif role == "hot_wallet" and nonce_i > 10000:
        risk = "high"
        findings.append(f"High activity EOA nonce={nonce_i}")
    elif role == "authority" and is_contract:
        risk = "medium"
        findings.append("Authority shows contract/delegation code")
    elif role.startswith("counterparty"):
        findings.append("Downstream USDT recipient — trace only")
    elif role == "operator_local":
        findings.append("Operator wallet — lab scope only")
    elif role == "primary_sink_hub" and is_contract:
        risk = "medium"
        findings.append("Bridge/sink contract in fund flow")

    if role == "hot_wallet":
        findings.append("Mass payout rail — entity attribution still required")

    status = "ACTIVE" if reachable and nonce_i > 0 else ("CONTRACT" if is_contract else "QUIET")
    return {
        "status": status,
        "risk_level": risk,
        "findings": findings,
        "recommended_action": _recommend(role, risk),
    }


def _recommend(role: str, risk: str) -> str:
    if role == "hot_wallet":
        return "Passive entity ID (Arkham/GitHub) + monitor outflows"
    if role == "authority":
        return "Read-only EIP-7702 bytecode audit; no exploit attempts"
    if role.startswith("counterparty"):
        return "Label propagation from public block explorer tags"
    if role == "operator_local":
        return "Operator lab only — harden keys and separate from target treasury"
    return "Continue read-only graph tracing"


def _bundle_summary(results: list[dict]) -> dict:
    high = [r for r in results if r.get("verdict", {}).get("risk_level") == "high"]
    medium = [r for r in results if r.get("verdict", {}).get("risk_level") == "medium"]
    active = [r for r in results if r.get("verdict", {}).get("status") == "ACTIVE"]
    return {
        "headline": f"{len(results)} wallets scanned — {len(active)} active, {len(high)} high-risk",
        "high_risk_roles": [r["role"] for r in high],
        "medium_risk_roles": [r["role"] for r in medium],
        "active_count": len(active),
    }


if __name__ == "__main__":
    raise SystemExit(main())
