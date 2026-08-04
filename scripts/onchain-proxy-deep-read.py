#!/usr/bin/env python3
"""
On-chain deep read для EVM proxy (EIP-1967) + Gnosis Safe + SELFDESTRUCT analysis.

Запуск без API-ключей (только публичный BSC RPC):
  python3 scripts/onchain-proxy-deep-read.py 0xb80a582fa430645a043bb4f6135321ee01005fef

Опционально BscScan metadata:
  export BSCSCAN_API_KEY=your_key
  python3 scripts/onchain-proxy-deep-read.py 0xb80a582f... --out ./artifacts

Зависимости: только stdlib (Python 3.10+).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- EIP-1967 slots (keccak(label) - 1) ---
SLOT_IMPLEMENTATION = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
SLOT_ADMIN = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
SLOT_BEACON = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"

DEFAULT_RPC = os.environ.get("BSC_RPC", "https://bsc-dataseed.binance.org")
BSCSCAN_API = os.environ.get("BSCSCAN_API_URL", "https://api.bscscan.com/api")

# eth_call selectors (first 4 bytes keccak)
SEL = {
    "admin()": "0xf851a440",
    "implementation()": "0x5c60da1b",
    "owner()": "0x8da5cb5b",
    "proxyAdmin()": "0x3f4ba83a",
    "getProxyImplementation(address)": "0x204e1c7a",
    "getProxyAdmin(address)": "0xf3b7dead",
    "getOwners()": "0xa0e67e2b",
    "getThreshold()": "0xe75235b8",
    "nonce()": "0xaffed0e0",
    "VERSION()": "0xffa1ad74",
}

OP_NAMES = {
    0x00: "STOP", 0x56: "JUMP", 0x57: "JUMPI", 0x5B: "JUMPDEST",
    0xF3: "RETURN", 0xF4: "DELEGATECALL", 0xFD: "REVERT", 0xFE: "INVALID",
    0xFF: "SELFDESTRUCT",
}


@dataclass
class Instr:
    offset: int
    opcode: int
    name: str
    arg: bytes | None = None
    size: int = 1


# ---------------------------------------------------------------------------
# RPC helpers
# ---------------------------------------------------------------------------

def rpc_call(rpc_url: str, method: str, params: list) -> Any:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(
        rpc_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "onchain-proxy-deep-read/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if data.get("error"):
        raise RuntimeError(f"RPC {method}: {data['error']}")
    return data.get("result")


def eth_call(rpc_url: str, to: str, data: str) -> tuple[str | None, str | None]:
    try:
        result = rpc_call(rpc_url, "eth_call", [{"to": to, "data": data}, "latest"])
        return result, None
    except RuntimeError as exc:
        return None, str(exc)


def get_code(rpc_url: str, address: str) -> bytes:
    raw = rpc_call(rpc_url, "eth_getCode", [address, "latest"]) or "0x"
    if raw in ("0x", "0X"):
        return b""
    return bytes.fromhex(raw[2:])


def get_balance_bnb(rpc_url: str, address: str) -> float:
    raw = rpc_call(rpc_url, "eth_getBalance", [address, "latest"])
    return int(raw, 16) / 1e18


def storage_address(rpc_url: str, contract: str, slot: str) -> str | None:
    raw = rpc_call(rpc_url, "eth_getStorageAt", [contract, slot, "latest"])
    if not raw or raw == "0x" + "0" * 64:
        return None
    return "0x" + raw[-40:].lower()


def encode_address_arg(selector: str, address: str) -> str:
    return selector + address.lower().replace("0x", "").rjust(64, "0")


def decode_address(ret: str | None) -> str | None:
    if not ret or ret in ("0x", "0x" + "0" * 64):
        return None
    return "0x" + ret[-40:].lower()


def decode_uint256(ret: str | None) -> int | None:
    if not ret:
        return None
    return int(ret, 16)


def decode_address_array(ret: str | None) -> list[str]:
    if not ret or ret == "0x":
        return []
    raw = ret[2:]
    if len(raw) < 128:
        return []
    offset = int(raw[0:64], 16) * 2
    length = int(raw[offset : offset + 64], 16)
    owners: list[str] = []
    base = offset + 64
    for i in range(length):
        word = raw[base + i * 64 : base + (i + 1) * 64]
        owners.append("0x" + word[-40:])
    return owners


def decode_version(ret: str | None) -> str | None:
    if not ret:
        return None
    raw = ret[2:]
    try:
        offset = int(raw[0:64], 16) * 2
        ln = int(raw[offset : offset + 64], 16)
        data = bytes.fromhex(raw[offset + 64 : offset + 64 + ln * 2])
        if data.isascii():
            return data.decode("ascii")
    except (ValueError, IndexError):
        pass
    return ret


def fetch_bscscan(address: str) -> dict[str, Any]:
    api_key = os.environ.get("BSCSCAN_API_KEY", "")
    params: dict[str, str] = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
    }
    if api_key:
        params["apikey"] = api_key
    url = f"{BSCSCAN_API}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "onchain-proxy-deep-read/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        rows = data.get("result")
        if isinstance(rows, list) and rows:
            row = rows[0]
            return {
                "contract_name": row.get("ContractName") or None,
                "proxy_flag": row.get("Proxy") == "1",
                "implementation_bscscan": (row.get("Implementation") or None),
                "source_verified": bool(row.get("SourceCode")),
                "compiler": row.get("CompilerVersion") or None,
            }
    except Exception as exc:
        return {"error": str(exc)}
    return {"source_verified": False}


# ---------------------------------------------------------------------------
# EVM disassembly + reachable SELFDESTRUCT
# ---------------------------------------------------------------------------

def disassemble(bytecode: bytes) -> list[Instr]:
    ins: list[Instr] = []
    i = 0
    n = len(bytecode)
    while i < n:
        off = i
        op = bytecode[i]
        if 0x60 <= op <= 0x7F:
            push_n = op - 0x5F
            i += 1
            arg = bytecode[i : i + push_n]
            if len(arg) < push_n:
                arg = arg.ljust(push_n, b"\x00")
            ins.append(Instr(off, op, f"PUSH{push_n}", arg, 1 + push_n))
            i += push_n
            continue
        if 0x80 <= op <= 0x8F:
            ins.append(Instr(off, op, f"DUP{op - 0x7F}"))
        elif 0x90 <= op <= 0x9F:
            ins.append(Instr(off, op, f"SWAP{op - 0x8F}"))
        else:
            ins.append(Instr(off, op, OP_NAMES.get(op, f"OP_{op:02x}")))
        i += 1
    return ins


def analyze_selfdestruct(bytecode: bytes) -> dict[str, Any]:
    ins = disassemble(bytecode)
    by_off = {x.offset: idx for idx, x in enumerate(ins)}
    jds = {x.offset for x in ins if x.opcode == 0x5B}
    sd_offs = [x.offset for x in ins if x.opcode == 0xFF]

    if not ins:
        return {
            "bytecode_bytes": len(bytecode),
            "total_instructions": 0,
            "selfdestruct_opcode_count": 0,
            "reachable_selfdestruct_count": 0,
            "raw_ff_byte_count": bytecode.count(b"\xff"),
        }

    seen: set[int] = set()
    stack = [0]
    reachable_sd: list[int] = []

    while stack:
        idx = stack.pop()
        if idx in seen or idx >= len(ins):
            continue
        seen.add(idx)
        cur = ins[idx]
        if cur.opcode == 0xFF:
            reachable_sd.append(cur.offset)
        if cur.opcode in (0x00, 0xF3, 0xFD, 0xFE, 0xFF):
            continue
        if cur.opcode == 0x56:
            if idx > 0:
                prev = ins[idx - 1]
                if prev.name.startswith("PUSH") and prev.arg is not None:
                    target = int.from_bytes(prev.arg, "big")
                    tidx = by_off.get(target)
                    if tidx is not None:
                        stack.append(tidx)
            continue
        if cur.opcode != 0x57 and idx + 1 < len(ins):
            stack.append(idx + 1)
        if cur.opcode == 0x57:
            if idx + 1 < len(ins):
                stack.append(idx + 1)
            if idx > 0:
                prev = ins[idx - 1]
                if prev.name.startswith("PUSH") and prev.arg is not None:
                    target = int.from_bytes(prev.arg, "big")
                    tidx = by_off.get(target)
                    if tidx is not None:
                        stack.append(tidx)

    return {
        "bytecode_bytes": len(bytecode),
        "total_instructions": len(ins),
        "jumpdest_count": len(jds),
        "raw_ff_byte_count": bytecode.count(b"\xff"),
        "selfdestruct_opcode_count": len(sd_offs),
        "reachable_selfdestruct_count": len(set(reachable_sd)),
        "reachable_selfdestruct_offsets": [hex(o) for o in sorted(set(reachable_sd))[:20]],
        "unreachable_selfdestruct_count": len(set(sd_offs) - set(reachable_sd)),
    }


# ---------------------------------------------------------------------------
# Safe / ProxyAdmin probes
# ---------------------------------------------------------------------------

def probe_proxy_admin(rpc_url: str, proxy_admin: str, proxy: str) -> dict[str, Any]:
    out: dict[str, Any] = {"address": proxy_admin}
    impl_data = encode_address_arg(SEL["getProxyImplementation(address)"], proxy)
    admin_data = encode_address_arg(SEL["getProxyAdmin(address)"], proxy)
    impl_ret, impl_err = eth_call(rpc_url, proxy_admin, impl_data)
    admin_ret, admin_err = eth_call(rpc_url, proxy_admin, admin_data)
    out["getProxyImplementation"] = decode_address(impl_ret) if not impl_err else f"revert: {impl_err}"
    out["getProxyAdmin"] = decode_address(admin_ret) if not admin_err else f"revert: {impl_err}"
    owner_ret, owner_err = eth_call(rpc_url, proxy_admin, SEL["owner()"])
    out["owner"] = decode_address(owner_ret) if not owner_err else f"revert: {owner_err}"
    out["balance_bnb"] = get_balance_bnb(rpc_url, proxy_admin)
    out["is_contract"] = len(get_code(rpc_url, proxy_admin)) > 0
    out["bscscan"] = fetch_bscscan(proxy_admin)
    return out


def probe_gnosis_safe(rpc_url: str, safe: str) -> dict[str, Any]:
    out: dict[str, Any] = {"address": safe}
    owners_ret, _ = eth_call(rpc_url, safe, SEL["getOwners()"])
    out["owners"] = decode_address_array(owners_ret)
    out["owner_count"] = len(out["owners"])
    thr_ret, thr_err = eth_call(rpc_url, safe, SEL["getThreshold()"])
    out["threshold"] = decode_uint256(thr_ret) if not thr_err else None
    nonce_ret, _ = eth_call(rpc_url, safe, SEL["nonce()"])
    out["nonce"] = decode_uint256(nonce_ret)
    ver_ret, _ = eth_call(rpc_url, safe, SEL["VERSION()"])
    out["version"] = decode_version(ver_ret)
    out["singleton_slot0"] = storage_address(rpc_url, safe, "0x0")
    out["balance_bnb"] = get_balance_bnb(rpc_url, safe)
    out["is_contract"] = len(get_code(rpc_url, safe)) > 0
    out["bscscan"] = fetch_bscscan(safe)
    if out["threshold"] is not None and out["owner_count"]:
        out["quorum_ru"] = f"{out['threshold']} из {out['owner_count']} подписей"
    return out


def probe_contract(rpc_url: str, address: str, label: str) -> dict[str, Any]:
    code = get_code(rpc_url, address)
    return {
        "label": label,
        "address": address,
        "balance_bnb": get_balance_bnb(rpc_url, address),
        "bytecode_bytes": len(code),
        "is_contract": len(code) > 0,
        "selfdestruct": analyze_selfdestruct(code),
        "bscscan": fetch_bscscan(address),
    }


# ---------------------------------------------------------------------------
# Main report
# ---------------------------------------------------------------------------

def analyze_proxy(rpc_url: str, proxy: str) -> dict[str, Any]:
    proxy = proxy.lower()
    ts = datetime.now(timezone.utc).isoformat()

    impl_slot = storage_address(rpc_url, proxy, SLOT_IMPLEMENTATION)
    admin_slot = storage_address(rpc_url, proxy, SLOT_ADMIN)
    beacon_slot = storage_address(rpc_url, proxy, SLOT_BEACON)

    eth_calls: dict[str, Any] = {}
    for name, sel in SEL.items():
        if "(" not in name or "address" in name:
            continue
        if name.startswith("get"):
            continue
        ret, err = eth_call(rpc_url, proxy, sel)
        eth_calls[name] = decode_address(ret) if not err else "revert"

    proxy_block = probe_contract(rpc_url, proxy, "proxy")
    proxy_block["eip1967"] = {
        "implementation": impl_slot,
        "admin": admin_slot,
        "beacon": beacon_slot,
    }
    proxy_block["eth_call"] = eth_calls

    implementation = impl_slot or eth_calls.get("implementation()")
    if isinstance(implementation, str) and implementation.startswith("0x") and len(implementation) == 42:
        impl_block = probe_contract(rpc_url, implementation, "implementation")
    else:
        impl_block = None
        implementation = impl_slot

    admin_addr = admin_slot
    if isinstance(admin_addr, str) and admin_addr.startswith("0x"):
        admin_block = probe_proxy_admin(rpc_url, admin_addr, proxy)
    else:
        admin_block = None

    safe_block = None
    safe_owner = None
    if admin_block and isinstance(admin_block.get("owner"), str) and admin_block["owner"].startswith("0x"):
        safe_owner = admin_block["owner"]
        code_len = len(get_code(rpc_url, safe_owner))
        if code_len > 0:
            owners_ret, _ = eth_call(rpc_url, safe_owner, SEL["getOwners()"])
            if decode_address_array(owners_ret):
                safe_block = probe_gnosis_safe(rpc_url, safe_owner)

    # fallback: owner() on proxy delegates to implementation owner
    owner_proxy = eth_calls.get("owner()")
    if safe_block is None and isinstance(owner_proxy, str) and owner_proxy.startswith("0x"):
        owners_ret, _ = eth_call(rpc_url, owner_proxy, SEL["getOwners()"])
        if decode_address_array(owners_ret):
            safe_block = probe_gnosis_safe(rpc_url, owner_proxy)

    sd_impl = (impl_block or {}).get("selfdestruct", {})
    verdict_ru = [
        f"Proxy {proxy}: баланс {proxy_block['balance_bnb']:.4f} BNB.",
        f"Implementation (EIP-1967): {implementation or '—'}.",
        f"Admin (EIP-1967): {admin_addr or '—'}.",
    ]
    if sd_impl:
        n = sd_impl.get("selfdestruct_opcode_count", 0)
        r = sd_impl.get("reachable_selfdestruct_count", 0)
        raw = sd_impl.get("raw_ff_byte_count", 0)
        if n == 0:
            verdict_ru.append(
                f"SELFDESTRUCT в implementation: **0 opcodes** (сырых 0xff в hex: {raw} — PUSH-данные)."
            )
        else:
            verdict_ru.append(
                f"SELFDESTRUCT: {n} opcodes, достижимых {r} — требуется ручной аудит."
            )
    if safe_block:
        verdict_ru.append(
            f"Gnosis Safe: quorum {safe_block.get('quorum_ru', 'n/a')}, nonce={safe_block.get('nonce')}."
        )
    elif admin_block and isinstance(admin_block.get("owner"), str):
        verdict_ru.append(f"Admin owner: {admin_block['owner']}.")

    return {
        "timestamp": ts,
        "rpc": rpc_url,
        "bscscan_api_key_used": bool(os.environ.get("BSCSCAN_API_KEY")),
        "proxy": proxy_block,
        "implementation": impl_block,
        "proxy_admin": admin_block,
        "gnosis_safe": safe_block,
        "verdict_ru": verdict_ru,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    proxy = report["proxy"]
    lines = [
        "# On-chain deep read (proxy + Safe + SELFDESTRUCT)",
        "",
        f"**Дата:** {report['timestamp']}",
        f"**RPC:** `{report['rpc']}`",
        f"**Proxy:** `{proxy['address']}`",
        "",
        "## Вердикт",
        "",
    ]
    for v in report.get("verdict_ru", []):
        lines.append(f"- {v}")
    lines += [
        "",
        "## EIP-1967",
        "",
        f"- Implementation: `{proxy['eip1967']['implementation']}`",
        f"- Admin: `{proxy['eip1967']['admin']}`",
        f"- Beacon: `{proxy['eip1967']['beacon'] or '—'}`",
        "",
        "## eth_call (proxy)",
        "",
    ]
    for k, v in proxy.get("eth_call", {}).items():
        lines.append(f"- `{k}` → `{v}`")

    impl = report.get("implementation")
    if impl:
        sd = impl["selfdestruct"]
        lines += [
            "",
            "## Implementation",
            "",
            f"- Адрес: `{impl['address']}`",
            f"- Байткод: {impl['bytecode_bytes']} bytes",
            f"- SELFDESTRUCT opcodes: **{sd['selfdestruct_opcode_count']}**",
            f"- Достижимых: **{sd['reachable_selfdestruct_count']}**",
            f"- Сырых 0xff в hex: {sd['raw_ff_byte_count']}",
        ]

    pa = report.get("proxy_admin")
    if pa:
        lines += ["", "## ProxyAdmin", "", f"- Адрес: `{pa['address']}`", f"- owner: `{pa.get('owner')}`"]

    safe = report.get("gnosis_safe")
    if safe:
        lines += [
            "",
            "## Gnosis Safe",
            "",
            f"- Адрес: `{safe['address']}`",
            f"- Threshold: **{safe.get('threshold')} / {safe.get('owner_count')}**",
            f"- Nonce: {safe.get('nonce')}",
            f"- Version: {safe.get('version')}",
            "",
            "### Owners",
        ]
        for i, o in enumerate(safe.get("owners", []), 1):
            lines.append(f"{i}. `{o}`")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deep on-chain read: EIP-1967 proxy + Safe + SELFDESTRUCT")
    parser.add_argument(
        "address",
        nargs="?",
        default="0xb80a582fa430645a043bb4f6135321ee01005fef",
        help="Proxy contract address (default: Rhino.fi Bridge BSC)",
    )
    parser.add_argument("--rpc", default=DEFAULT_RPC, help="BSC JSON-RPC URL")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/onchain-deep-read"),
        help="Output directory for JSON + Markdown",
    )
    args = parser.parse_args()

    try:
        report = analyze_proxy(args.rpc, args.address)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    short = args.address.lower().replace("0x", "")[:8]
    json_path = args.out / f"deep-read-{short}.json"
    md_path = args.out / f"deep-read-{short}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, md_path)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nSaved: {json_path}\n       {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
