#!/usr/bin/env python3
"""
Slither + Mythril batch для BSC контрактов (defense / read-only triage).

Важно:
  - Slither по адресу: `slither bsc:0x...` (не просто 0x...)
  - Для загрузки verified source нужен BSCSCAN_API_KEY (Etherscan API v2 / BscScan)
  - Mythril опционален; анализирует bytecode через RPC если нет исходника

Примеры:
  export BSCSCAN_API_KEY=your_key
  export BSC_RPC=http://51.222.42.220:8545
  python3 scripts/run-slither-mythril-audit.py \\
    0x5ab2790be0ade18af686f38c5321af1d8daa3192 \\
    0xb8ee2cd0e210fac991e441dba767082d9cdceec3

  python3 scripts/run-slither-mythril-audit.py --addresses-file targets.txt --out artifacts/audit
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_RPC = os.environ.get("BSC_RPC", "https://bsc-dataseed.binance.org")
BSCSCAN_API = os.environ.get("BSCSCAN_API_URL", "https://api.bscscan.com/api")
ETHERSCAN_V2 = os.environ.get("ETHERSCAN_API_URL", "https://api.etherscan.io/v2/api")

DEFAULT_TARGETS = [
    ("implementation", "0x5ab2790be0ade18af686f38c5321af1d8daa3192"),
    ("proxy_admin", "0xb8ee2cd0e210fac991e441dba767082d9cdceec3"),
]

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "informational": 3, "optimization": 4, "unknown": 5}


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def fetch_bscscan_source(address: str) -> dict[str, Any]:
    api_key = os.environ.get("BSCSCAN_API_KEY", "")
    params = {"module": "contract", "action": "getsourcecode", "address": address.lower()}
    if api_key:
        params["apikey"] = api_key
    url = f"{BSCSCAN_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "run-slither-mythril-audit/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    rows = data.get("result") if isinstance(data.get("result"), list) else []
    if not rows:
        return {"ok": False, "error": "empty bscscan response", "source_available": False}
    row = rows[0]
    src = row.get("SourceCode") or ""
    return {
        "ok": bool(src),
        "contract_name": row.get("ContractName"),
        "compiler": row.get("CompilerVersion"),
        "source_code": src,
        "abi": row.get("ABI"),
        "proxy": row.get("Proxy") == "1",
        "implementation": row.get("Implementation") or None,
        "source_available": bool(src),
    }


def write_source_tree(address: str, meta: dict[str, Any], out_dir: Path) -> Path | None:
    src = meta.get("source_code") or ""
    if not src:
        return None
    contract_dir = out_dir / address.lower()
    contract_dir.mkdir(parents=True, exist_ok=True)
    name = (meta.get("contract_name") or "Contract").replace(" ", "_")
    # Standard JSON input {{...}} from BscScan
    if src.startswith("{{"):
        payload = json.loads(src[1:-1])
        sources = payload.get("sources", {})
        for fname, body in sources.items():
            content = body.get("content", "") if isinstance(body, dict) else str(body)
            path = contract_dir / fname
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        (contract_dir / "crytic_compile.config.json").write_text(
            json.dumps({"solc_remaps": [], "solc_version": meta.get("compiler")}, indent=2),
            encoding="utf-8",
        )
        return contract_dir
    if src.startswith("{"):
        payload = json.loads(src)
        sources = payload.get("sources", {})
        for fname, body in sources.items():
            content = body.get("content", "") if isinstance(body, dict) else str(body)
            path = contract_dir / fname
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return contract_dir
    # flat single file
    path = contract_dir / f"{name}.sol"
    path.write_text(src, encoding="utf-8")
    return contract_dir


def run_cmd(cmd: list[str], timeout: int = 600) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "ok": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "ok": False, "error": "timeout", "returncode": -1}
    except FileNotFoundError:
        return {"cmd": cmd, "ok": False, "error": "not_found", "returncode": 127}


def run_slither(address: str, label: str, work_dir: Path, artifacts: Path) -> dict[str, Any]:
    slither = which("slither")
    out: dict[str, Any] = {"tool": "slither", "address": address, "label": label}
    if not slither:
        out["status"] = "skipped"
        out["reason"] = "slither not installed (pip install slither-analyzer)"
        return out

    json_path = artifacts / f"slither-{label}-{address[2:10]}.json"
    target_onchain = f"bsc:{address.lower()}"

    # 1) on-chain via crytic / etherscan v2 (needs API key)
    api_key = os.environ.get("BSCSCAN_API_KEY") or os.environ.get("ETHERSCAN_API_KEY")
    env = os.environ.copy()
    if api_key:
        env["ETHERSCAN_API_KEY"] = api_key
        env["BSCSCAN_API_KEY"] = api_key

    proc = run_cmd([slither, target_onchain, "--json", str(json_path)], timeout=900)
    out["onchain_attempt"] = {
        "target": target_onchain,
        "api_key_set": bool(api_key),
        "returncode": proc.get("returncode"),
        "stderr_tail": (proc.get("stderr") or "")[-1500:],
    }

    if proc.get("ok") and json_path.is_file():
        out["status"] = "ok"
        out["json_path"] = str(json_path)
        out["findings"] = parse_slither_json(json_path)
        return out

    # 2) fallback: fetch source + analyze directory
    meta = fetch_bscscan_source(address)
    out["bscscan_fetch"] = {k: v for k, v in meta.items() if k != "source_code"}
    if not meta.get("source_available"):
        out["status"] = "failed"
        out["reason"] = "no source (set BSCSCAN_API_KEY for on-chain slither)"
        return out

    src_dir = write_source_tree(address, meta, work_dir)
    if not src_dir:
        out["status"] = "failed"
        out["reason"] = "could not materialize source tree"
        return out

    proc2 = run_cmd([slither, str(src_dir), "--json", str(json_path)], timeout=900)
    out["local_attempt"] = {
        "source_dir": str(src_dir),
        "returncode": proc2.get("returncode"),
        "stderr_tail": (proc2.get("stderr") or "")[-1500:],
    }
    if json_path.is_file():
        out["status"] = "ok" if proc2.get("returncode") == 0 else "ok_with_findings"
        out["json_path"] = str(json_path)
        out["findings"] = parse_slither_json(json_path)
    else:
        out["status"] = "failed"
        out["reason"] = proc2.get("stderr", "slither produced no json")[-500:]
    return out


def parse_slither_json(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    detectors = data.get("results", {}).get("detectors", [])
    findings = []
    for d in detectors:
        findings.append(
            {
                "check": d.get("check"),
                "impact": (d.get("impact") or "unknown").lower(),
                "confidence": d.get("confidence"),
                "description": d.get("description"),
                "first_markdown_element": d.get("first_markdown_element"),
            }
        )
    findings.sort(key=lambda x: SEVERITY_ORDER.get(x.get("impact", "unknown"), 99))
    return findings


def run_mythril(address: str, label: str, rpc: str, artifacts: Path) -> dict[str, Any]:
    myth = which("myth") or which("mythril")
    out: dict[str, Any] = {"tool": "mythril", "address": address, "label": label}
    if not myth:
        out["status"] = "skipped"
        out["reason"] = "mythril not installed (pip install mythril)"
        return out

    json_path = artifacts / f"mythril-{label}-{address[2:10]}.json"
    cmd = [
        myth,
        "analyze",
        "-a",
        address.lower(),
        "--rpc",
        rpc,
        "-o",
        "json",
        "--execution-timeout",
        "120",
    ]
    proc = run_cmd(cmd, timeout=600)
    stdout = proc.get("stdout") or ""
    if stdout.strip():
        json_path.write_text(stdout, encoding="utf-8")
    elif proc.get("stderr"):
        json_path.write_text(json.dumps({"stderr": proc["stderr"]}, indent=2), encoding="utf-8")

    out["attempt"] = {"cmd": cmd, "returncode": proc.get("returncode"), "json_path": str(json_path)}
    findings = parse_mythril_json(json_path)
    out["findings"] = findings
    out["status"] = "ok" if findings or proc.get("returncode") == 0 else "failed"
    if not findings and proc.get("returncode") != 0:
        out["reason"] = (proc.get("stderr") or "")[-800:]
    return out


def parse_mythril_json(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict) and "issues" in data:
        issues = data["issues"]
    elif isinstance(data, list):
        issues = data
    else:
        issues = data.get("results", []) if isinstance(data, dict) else []
    findings = []
    for item in issues:
        if not isinstance(item, dict):
            continue
        findings.append(
            {
                "title": item.get("title") or item.get("swc-id") or item.get("swc_id"),
                "severity": (item.get("severity") or "unknown").lower(),
                "description": item.get("description") or item.get("details"),
                "swc_id": item.get("swc-id") or item.get("swc_id"),
            }
        )
    return findings


def merge_report(targets: list[tuple[str, str]], results: list[dict[str, Any]]) -> dict[str, Any]:
    unified_findings: list[dict[str, Any]] = []
    for block in results:
        tool = block.get("tool")
        label = block.get("label")
        addr = block.get("address")
        for f in block.get("findings") or []:
            unified_findings.append(
                {
                    "tool": tool,
                    "label": label,
                    "address": addr,
                    **f,
                }
            )
    unified_findings.sort(
        key=lambda x: (
            SEVERITY_ORDER.get(str(x.get("impact") or x.get("severity") or "unknown"), 99),
            x.get("tool", ""),
        )
    )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "targets": [{"label": l, "address": a} for l, a in targets],
        "tools_available": {"slither": bool(which("slither")), "mythril": bool(which("myth") or which("mythril"))},
        "bscscan_api_key_set": bool(os.environ.get("BSCSCAN_API_KEY")),
        "rpc": os.environ.get("BSC_RPC", DEFAULT_RPC),
        "results": results,
        "unified_findings": unified_findings,
        "summary_ru": summarize_ru(results, unified_findings),
    }


def summarize_ru(results: list[dict[str, Any]], unified: list[dict[str, Any]]) -> list[str]:
    lines = []
    for block in results:
        tool = block.get("tool")
        label = block.get("label")
        status = block.get("status")
        n = len(block.get("findings") or [])
        lines.append(f"{tool} / {label}: status={status}, findings={n}")
    high = [f for f in unified if str(f.get("impact") or f.get("severity")) in ("high", "critical")]
    if high:
        lines.append(f"Критичных/high находок в сводке: {len(high)}")
    else:
        lines.append("Критичных/high находок в сводке: 0 (или инструменты не отработали)")
    return lines


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Slither + Mythril audit report",
        "",
        f"**Дата:** {report['timestamp']}",
        f"**BSCSCAN_API_KEY:** {'да' if report['bscscan_api_key_set'] else 'нет'}",
        "",
        "## Сводка",
        "",
    ]
    for s in report.get("summary_ru", []):
        lines.append(f"- {s}")
    lines += ["", "## Unified findings", ""]
    if not report.get("unified_findings"):
        lines.append("_Находок нет или анализ не выполнен._")
    for f in report.get("unified_findings", [])[:50]:
        sev = f.get("impact") or f.get("severity") or "?"
        title = f.get("check") or f.get("title") or "finding"
        lines.append(f"- **[{sev}]** `{f.get('tool')}` / `{f.get('label')}` — {title}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_addresses_file(path: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 1:
            out.append((f"target_{i}", parts[0]))
        else:
            out.append((parts[0], parts[1]))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Slither + Mythril batch for BSC contracts")
    parser.add_argument("addresses", nargs="*", help="0x addresses (optional if --addresses-file)")
    parser.add_argument("--addresses-file", type=Path, help="file: label address per line")
    parser.add_argument("--out", type=Path, default=Path("artifacts/slither-mythril"))
    parser.add_argument("--rpc", default=DEFAULT_RPC)
    parser.add_argument("--skip-mythril", action="store_true")
    parser.add_argument("--skip-slither", action="store_true")
    args = parser.parse_args()

    if args.addresses_file:
        targets = load_addresses_file(args.addresses_file)
    elif args.addresses:
        targets = [(f"target_{i+1}", a) for i, a in enumerate(args.addresses)]
    else:
        targets = DEFAULT_TARGETS

    args.out.mkdir(parents=True, exist_ok=True)
    work_dir = args.out / "sources"
    work_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("BSC_RPC", args.rpc)

    results: list[dict[str, Any]] = []
    for label, address in targets:
        if not args.skip_slither:
            results.append(run_slither(address, label, work_dir, args.out))
        if not args.skip_mythril:
            results.append(run_mythril(address, label, args.rpc, args.out))

    report = merge_report(targets, results)
    json_path = args.out / "unified-audit-report.json"
    md_path = args.out / "unified-audit-report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, md_path)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nSaved: {json_path}\n       {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
