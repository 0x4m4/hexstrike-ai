#!/usr/bin/env python3
"""Read-only BSC recon: balances, code, USDT allowance for operator."""
import json
import urllib.request

RPC = "http://51.222.42.220:8545"
USDT = "0x55d398326f99059f775485246999027b3197955"
TARGETS = {
    "puissant_validator": "0x4848489f0b2bedd788c696e2d79b6b69d7484848",
    "hot_wallet": "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
    "operator": "0x85dB346BE1d9d5D8ec4F57acf0067FbE53a6E846",
}


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        out = json.load(r)
    if "error" in out:
        raise RuntimeError(out["error"])
    return out["result"]


def to_int(hexv):
    return int(hexv, 16)


def pad_addr(addr):
    return addr.lower().replace("0x", "").zfill(64)


def erc20_balance(token, holder):
    data = "0x70a08231" + pad_addr(holder)
    raw = rpc("eth_call", [{"to": token, "data": data}, "latest"])
    return to_int(raw) / 1e18


def allowance(token, owner, spender):
    # allowance(address,address)
    data = "0xdd62ed3e" + pad_addr(owner) + pad_addr(spender)
    raw = rpc("eth_call", [{"to": token, "data": data}, "latest"])
    return to_int(raw) / 1e18


def main():
    report = {"rpc": RPC, "targets": {}}
    for name, addr in TARGETS.items():
        bal_wei = to_int(rpc("eth_getBalance", [addr, "latest"]))
        nonce = to_int(rpc("eth_getTransactionCount", [addr, "latest"]))
        code = rpc("eth_getCode", [addr, "latest"])
        usdt = erc20_balance(USDT, addr)
        entry = {
            "address": addr,
            "bnb": bal_wei / 1e18,
            "nonce": nonce,
            "is_contract": code not in ("0x", "0x0", None),
            "usdt": usdt,
        }
        report["targets"][name] = entry

    op = TARGETS["operator"]
    report["allowances_usdt_to_operator"] = {}
    for name in ("puissant_validator", "hot_wallet"):
        owner = TARGETS[name]
        try:
            report["allowances_usdt_to_operator"][name] = allowance(USDT, owner, op)
        except Exception as e:
            report["allowances_usdt_to_operator"][name] = f"error: {e}"

    # reverse: operator -> targets
    report["allowances_usdt_from_operator"] = {}
    for name in ("puissant_validator", "hot_wallet"):
        spender = TARGETS[name]
        try:
            report["allowances_usdt_from_operator"][name] = allowance(USDT, op, spender)
        except Exception as e:
            report["allowances_usdt_from_operator"][name] = f"error: {e}"

    print(json.dumps(report, indent=2))
    out = "/workspace/artifacts/bsc-phase-a.json"
    import os
    os.makedirs("/workspace/artifacts", exist_ok=True)
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
