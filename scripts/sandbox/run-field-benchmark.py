#!/usr/bin/env python3
"""Field benchmark: multi-wallet BSC recon + conclusions (N runs)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = Path(__file__).resolve().parent
RUNS = int(os.environ.get("FIELD_RUNS", "10"))
REPORT = ROOT / "artifacts" / "sandbox" / "field-runs-benchmark.json"
ORCH = ROOT / "hexstrike-orchestrator"


def run_workflow() -> dict:
    run_id = uuid.uuid4().hex[:12]
    env = {**os.environ, "ORCHESTRATOR_RUN_ID": run_id, "ORCHESTRATOR_WORKFLOW": "field-benchmark"}
    started = time.time()
    proc = subprocess.run(
        [str(ORCH), "run", "multi-wallet-conclusions", "--quiet"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    elapsed = round(time.time() - started, 2)

    conclusion = {}
    bundle = {}
    cp = ROOT / "artifacts" / "sandbox" / "target-conclusion.json"
    bp = ROOT / "artifacts" / "sandbox" / "target-recon-bundle.json"
    if cp.is_file():
        conclusion = json.loads(cp.read_text(encoding="utf-8"))
    if bp.is_file():
        bundle = json.loads(bp.read_text(encoding="utf-8"))

    hot = next((w for w in bundle.get("wallets", []) if w.get("role") == "hot_wallet"), {})
    return {
        "run_id": run_id,
        "success": proc.returncode == 0,
        "exit_code": proc.returncode,
        "elapsed_sec": elapsed,
        "headline": conclusion.get("overall", {}).get("headline"),
        "risk_posture": conclusion.get("overall", {}).get("risk_posture"),
        "entity_status": conclusion.get("overall", {}).get("entity_status"),
        "wallet_count": bundle.get("wallet_count"),
        "hot_wallet_live": hot.get("live"),
        "hot_verdict": hot.get("verdict"),
        "fork_active": bundle.get("fork_active"),
        "stderr_tail": (proc.stderr or "")[-400:],
    }


def main() -> int:
    print(f"=== FIELD RUNS BENCHMARK ({RUNS}× multi-wallet-conclusions) ===")
    print(f"Target: BSC live + fork | Read-only")
    print()

    # One-time fork setup before field series
    subprocess.run(["bash", str(SANDBOX / "setup-real-target-fork.sh")], cwd=str(ROOT), check=False)

    results = []
    for i in range(1, RUNS + 1):
        print(f"[field {i}/{RUNS}] ", end="", flush=True)
        row = run_workflow()
        results.append(row)
        icon = "✓" if row["success"] else "✗"
        hot = row.get("hot_wallet_live") or {}
        print(
            f"{icon} {row['elapsed_sec']}s | "
            f"hot={hot.get('balance_eth', '?')} ETH nonce={hot.get('nonce', '?')} | "
            f"{row.get('headline', 'no headline')}"
        )
        time.sleep(1)  # RPC courtesy pause

    ok = sum(1 for r in results if r["success"])
    times = [r["elapsed_sec"] for r in results]
    nonces = [
        int(r["hot_wallet_live"]["nonce"])
        for r in results
        if r.get("hot_wallet_live", {}).get("nonce", "").isdigit()
    ]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "field_read_only",
        "workflow": "multi-wallet-conclusions",
        "runs": RUNS,
        "passed": ok,
        "failed": RUNS - ok,
        "pass_rate": round(100 * ok / RUNS, 1),
        "timing_sec": {
            "min": min(times) if times else 0,
            "max": max(times) if times else 0,
            "avg": round(sum(times) / len(times), 2) if times else 0,
        },
        "hot_wallet_nonce_drift": (max(nonces) - min(nonces)) if nonces else None,
        "consistent_verdict": len({r.get("headline") for r in results}) == 1,
        "results": results,
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print()
    print("=== FIELD SUMMARY ===")
    print(f"  Pass: {ok}/{RUNS} ({report['pass_rate']}%)")
    print(f"  Time: avg={report['timing_sec']['avg']}s min={report['timing_sec']['min']}s max={report['timing_sec']['max']}s")
    if nonces:
        print(f"  Hot wallet nonce range: {min(nonces)} → {max(nonces)} (drift {report['hot_wallet_nonce_drift']})")
    print(f"  Verdict stable: {report['consistent_verdict']}")
    print(f"  Report: {REPORT}")
    return 0 if ok == RUNS else 1


if __name__ == "__main__":
    raise SystemExit(main())
