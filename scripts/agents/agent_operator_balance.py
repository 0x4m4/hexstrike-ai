#!/usr/bin/env python3
"""Operator wallet balance check (read-only RPC)."""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "artifacts/operator-balance.json"
OPERATOR = os.environ.get("OPERATOR_ADDRESS", "0x85dB346BE1d9d5D8ec4F57acf0067FbE53a6E846")
BSC_RPC = os.environ.get("BSC_RPC", "https://bsc-dataseed.binance.org/")
USDT_BSC = "0x55d398326f99059fF775485246999027B3197955"


def rpc(method: str, params: list) -> str:
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(BSC_RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["result"]


def balance_of(token: str, holder: str) -> int:
    addr = holder.lower().replace("0x", "").zfill(64)
    data = "0x70a08231" + addr
    result = rpc("eth_call", [{"to": token, "data": data}, "latest"])
    return int(result, 16)


def main() -> int:
    out = Path(os.environ.get("OUTPUT", DEFAULT_OUT))
    bnb_wei = int(rpc("eth_getBalance", [OPERATOR, "latest"]), 16)
    usdt_raw = balance_of(USDT_BSC, OPERATOR)
    bnb = bnb_wei / 1e18
    usdt = usdt_raw / 1e18

    gas_ok = bnb >= 0.001
    usdt_ok = usdt >= 0.01
    ready = gas_ok and usdt_ok

    if not usdt_ok:
        action = {
            "step": "manual_binance_withdraw",
            "what": "USDT",
            "amount_suggested": "10-20 USDT",
            "network": "BSC (BEP-20)",
            "address": OPERATOR,
            "note": "Orchestrator cannot withdraw from Binance — user action required",
        }
    elif ready:
        action = {
            "step": "run_send_proof",
            "command": (
                f"TO={OPERATOR} AMOUNT=0.01 NETWORK=bsc CONFIRM=yes node ~/send-proof.js"
            ),
        }
    else:
        action = {"step": "wait", "note": "check balances"}

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "Agent-Report-06",
        "task": "operator-balance-check",
        "operator": OPERATOR,
        "bsc_rpc": BSC_RPC,
        "balances": {"bnb": bnb, "usdt": usdt},
        "checks": {
            "gas_ok": gas_ok,
            "usdt_ok": usdt_ok,
            "ready_for_send_proof": ready,
        },
        "next_action": action,
        "bscscan": f"https://bscscan.com/address/{OPERATOR}",
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps({"success": True, "output": str(out), "bnb": bnb, "usdt": usdt, "ready": ready}))
    print(f"BNB : {bnb:.8f} {'OK' if gas_ok else 'LOW'}")
    print(f"USDT: {usdt:.4f} {'OK' if usdt_ok else 'DEPOSIT 10-20 USDT from Binance BEP-20'}")
    if not usdt_ok:
        print(f"→ Withdraw USDT (BEP-20) to {OPERATOR}")
    else:
        print(f"→ Ready: {action['command']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
