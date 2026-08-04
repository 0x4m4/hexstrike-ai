#!/usr/bin/env python3
"""
Batch on-chain probe: targets JSON → deep-read (+ optional agent) → unified-report.

Примеры:
  python3 scripts/run-field-batch.py
  python3 scripts/run-field-batch.py --targets scripts/sandbox/field-targets-5-batch2.json
  python3 scripts/run-field-batch.py --targets scripts/sandbox/field-targets-5.json --parallel 3
  BSC_RPC=http://51.222.42.220:8545 python3 scripts/run-field-batch.py --with-agent
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEEP_READ = ROOT / "scripts" / "onchain-proxy-deep-read.py"
AGENT_ONCHAIN = ROOT / "dual-mode-agent" / "agent_dual_mode.py"
DEFAULT_TARGETS = ROOT / "scripts" / "sandbox" / "field-targets-5-batch2.json"
DEFAULT_RPC = os.environ.get("BSC_RPC", "https://bsc-dataseed.binance.org")
EIP7702_PREFIX = "ef0100"


def load_targets(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    wallets = data.get("wallets") or data.get("targets") or []
    if not wallets:
        raise ValueError(f"No wallets in {path}")
    return wallets


def rpc_get_code(address: str, rpc: str) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getCode",
        "params": [address.lower(), "latest"],
    }
    req = urllib.request.Request(
        rpc,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        out = json.loads(resp.read().decode())
    return (out.get("result") or "0x").lower()


def classify_address(address: str, rpc: str, deep: dict[str, Any] | None) -> dict[str, Any]:
    code = rpc_get_code(address, rpc)
    body = code[2:] if code.startswith("0x") else code
    info: dict[str, Any] = {
        "bytecode_bytes": len(body) // 2,
        "is_contract": len(body) > 0,
    }
    if body.startswith(EIP7702_PREFIX) and len(body) >= 46:
        info["type"] = "eip7702_delegator"
        info["delegated_implementation"] = "0x" + body[6:46]
    elif deep and deep.get("proxy", {}).get("eip1967", {}).get("implementation"):
        info["type"] = "eip1967_proxy"
        info["implementation"] = deep["proxy"]["eip1967"]["implementation"]
    elif info["is_contract"]:
        info["type"] = "contract"
    else:
        info["type"] = "eoa"
    return info


def run_deep_read(address: str, role: str, out_dir: Path, rpc: str) -> dict[str, Any]:
    role_dir = out_dir / role
    role_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(DEEP_READ), address, "--rpc", rpc, "--out", str(role_dir)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    short = address.lower().replace("0x", "")[:8]
    json_path = role_dir / f"deep-read-{short}.json"
    result: dict[str, Any] = {
        "tool": "onchain-proxy-deep-read",
        "status": "ok" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "json_path": str(json_path) if json_path.is_file() else None,
    }
    if json_path.is_file():
        result["data"] = json.loads(json_path.read_text(encoding="utf-8"))
    elif proc.stdout.strip():
        try:
            result["data"] = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result["stderr"] = (proc.stderr or proc.stdout)[-800:]
    else:
        result["stderr"] = (proc.stderr or "")[-800:]
    return result


def run_agent_onchain(address: str) -> dict[str, Any]:
    if not AGENT_ONCHAIN.is_file():
        return {"tool": "agent-onchain", "status": "skipped", "reason": "dual-mode-agent not found"}
    proc = subprocess.run(
        [sys.executable, str(AGENT_ONCHAIN), "onchain", address],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(AGENT_ONCHAIN.parent),
    )
    if proc.returncode != 0:
        return {"tool": "agent-onchain", "status": "failed", "stderr": proc.stderr[-800:]}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"tool": "agent-onchain", "status": "failed", "stderr": proc.stdout[-800:]}
    return {
        "tool": "agent-onchain",
        "status": "ok" if data.get("success") else "failed",
        "verdict": data.get("verdict"),
        "artifacts": data.get("artifacts"),
    }


def process_target(
    wallet: dict[str, Any],
    out_dir: Path,
    rpc: str,
    with_agent: bool,
) -> dict[str, Any]:
    role = wallet.get("role") or "target"
    address = wallet["address"]
    entry: dict[str, Any] = {
        "role": role,
        "address": address,
        "chain": wallet.get("chain", "BSC"),
        "context": wallet.get("context", {}),
    }
    deep = run_deep_read(address, role, out_dir, rpc)
    entry["deep_read"] = deep
    deep_data = deep.get("data") or {}
    entry["classification"] = classify_address(address, rpc, deep_data)

    if with_agent:
        entry["agent"] = run_agent_onchain(address)

    # quick verdict from agent or deep-read
    if entry.get("agent", {}).get("verdict"):
        v = entry["agent"]["verdict"]
        entry["priority"] = v.get("priority")
        entry["risk_score_10"] = v.get("risk_score_10")
        entry["headline_ru"] = v.get("headline_ru")
    else:
        proxy = deep_data.get("proxy") or {}
        bal = proxy.get("balance_bnb")
        entry["headline_ru"] = f"{role}: {entry['classification'].get('type')} balance_bnb={bal}"

    return entry


def build_eip7702_clusters(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: dict[str, list[str]] = {}
    for r in results:
        cl = r.get("classification") or {}
        if cl.get("type") == "eip7702_delegator":
            impl = cl.get("delegated_implementation", "").lower()
            clusters.setdefault(impl, []).append(r["address"].lower())
    return [{"implementation": impl, "delegators": addrs} for impl, addrs in clusters.items()]


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Field batch report",
        "",
        f"**Дата:** {report['timestamp']}",
        f"**Targets file:** `{report['targets_file']}`",
        f"**RPC:** `{report['rpc']}`",
        f"**Обработано:** {report['count']}",
        "",
        "## Сводка",
        "",
        "| Роль | Адрес | Тип | Приоритет | Оценка | BNB |",
        "|------|-------|-----|-----------|--------|-----|",
    ]
    priority_rank = {"высокий": 0, "средний": 1, "низкий": 2, "информационный": 3}
    sorted_results = sorted(
        report["results"],
        key=lambda x: (
            priority_rank.get(str(x.get("priority")), 9),
            -(x.get("risk_score_10") or 0),
        ),
    )
    for r in sorted_results:
        cl = r.get("classification", {})
        bal = ((r.get("deep_read") or {}).get("data") or {}).get("proxy", {}).get("balance_bnb")
        bal_s = f"{bal:.2f}" if isinstance(bal, (int, float)) else "—"
        lines.append(
            f"| {r['role']} | `{r['address'][:10]}…` | {cl.get('type','?')} "
            f"| {r.get('priority','—')} | {r.get('risk_score_10','—')} | {bal_s} BNB |"
        )
    clusters = report.get("eip7702_clusters") or []
    if clusters:
        lines += ["", "## EIP-7702 clusters", ""]
        for c in clusters:
            lines.append(f"- **impl** `{c['implementation']}` → {len(c['delegators'])} delegator(s)")
            for d in c["delegators"]:
                lines.append(f"  - `{d}`")
    lines += ["", "## Заблокировано / пропущено", ""]
    blocked = report.get("blocked") or []
    if blocked:
        for b in blocked:
            lines.append(f"- {b}")
    else:
        lines.append("- —")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch on-chain field probe")
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--rpc", default=DEFAULT_RPC)
    parser.add_argument("--parallel", type=int, default=3)
    parser.add_argument("--with-agent", action="store_true", help="Also run dual-mode-agent onchain")
    args = parser.parse_args()

    if not DEEP_READ.is_file():
        print(f"ERROR: missing {DEEP_READ}", file=sys.stderr)
        return 1
    if not args.targets.is_file():
        print(f"ERROR: targets not found: {args.targets}", file=sys.stderr)
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or (ROOT / "artifacts" / "field-runs" / ts)
    out_dir.mkdir(parents=True, exist_ok=True)

    wallets = load_targets(args.targets)
    results: list[dict[str, Any]] = []
    blocked: list[str] = []

    if not os.environ.get("BSCSCAN_API_KEY"):
        blocked.append("BSCSCAN_API_KEY не задан — Slither/source metadata ограничены")

    workers = max(1, min(args.parallel, len(wallets)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(process_target, w, out_dir, args.rpc, args.with_agent): w for w in wallets
        }
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                w = futures[fut]
                results.append({
                    "role": w.get("role"),
                    "address": w.get("address"),
                    "error": str(exc),
                })

    results.sort(key=lambda x: x.get("role", ""))
    report: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "targets_file": str(args.targets),
        "rpc": args.rpc,
        "count": len(results),
        "with_agent": args.with_agent,
        "results": results,
        "eip7702_clusters": build_eip7702_clusters(results),
        "blocked": blocked,
    }

    json_path = out_dir / "unified-report.json"
    md_path = out_dir / "SUMMARY.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, md_path)

    print(json.dumps({
        "out": str(out_dir),
        "count": len(results),
        "clusters": len(report["eip7702_clusters"]),
        "json": str(json_path),
        "markdown": str(md_path),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
