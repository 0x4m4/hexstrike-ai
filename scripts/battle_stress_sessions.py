#!/usr/bin/env python3
"""Two-session battle stress test: 5× defense + 5× attack (inspector TZ)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "cmd" / "agent"
OUT_DIR = ROOT / "artifacts" / "stress_test"
REPORT_GLOB = ROOT / "test_report_{mode}_{run:02d}.json"
SUMMARY_PATH = ROOT / "artifacts" / "stress_test" / "battle_sessions_summary.json"

RECON_IP = "51.250.97.223"
ALLOWED_FUNDER = "0x730ea0231808f42a20f8921ba7fbc788226768f5"
ATTACKER = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
VICTIM = "0xcfc85f21f5f01ab24d6b7a3b93ef097099ebde3a"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def shell(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
    )
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def go_test_all() -> dict[str, Any]:
    return shell(["go", "test", "./...", "-count=1"], cwd=AGENT_DIR)


def go_engine_defense_cases() -> dict[str, Any]:
    """Run orchestrator package tests = attacks #02/#04/#06 defense paths."""
    r = shell(
        ["go", "test", "./internal/orchestrator/", "-count=1", "-v"],
        cwd=AGENT_DIR,
    )
    attacks = {
        "02-race-duplicate-sign": "DEFENDED" if "TestPrepareRescueDedup" in r["stdout"] and "PASS" in r["stdout"] else "UNKNOWN",
        "04-replay-rescue-tx": "DEFENDED" if "TestPrepareRescueDedup" in r["stdout"] else "UNKNOWN",
        "06-compromised-funder": "DEFENDED" if "TestPrepareRescueCompromisedFunderBlocked" in r["stdout"] and "PASS" in r["stdout"] else "UNKNOWN",
    }
    if r["exit_code"] != 0:
        attacks = {k: "FAIL" for k in attacks}
    return {**r, "attacks": attacks}


def go_hot_path_latency_ms() -> dict[str, Any]:
    """Micro-benchmark PrepareRescue via go test -bench if available; fallback test elapsed."""
    r = shell(
        ["go", "test", "./internal/orchestrator/", "-run=^$", "-bench=.", "-benchtime=5x", "-count=1"],
        cwd=AGENT_DIR,
    )
    latency_ms = None
    for line in (r["stdout"] or "").splitlines():
        if "ns/op" in line:
            try:
                ns = float(line.split()[2])
                latency_ms = round(ns / 1e6, 3)
            except (IndexError, ValueError):
                pass
    if latency_ms is None:
        er = go_engine_defense_cases()
        latency_ms = round(er["elapsed_sec"] * 1000 / 5, 2)
    return {"latency_ms_hot_path": latency_ms, "bench_stdout": (r["stdout"] or "")[-400:]}


def run_field_pipeline() -> dict[str, Any]:
    orch = ROOT / "scripts" / "hexstrike-orchestrator.py"
    env = {
        "ORCHESTRATOR_WORKFLOW": "field-targets-5",
        "WALLETS_FILE": "scripts/sandbox/field-targets-5.json",
        "WALLETS_ONLY": "1",
    }
    if os.environ.get("ALLOWED_FUNDERS"):
        env["ALLOWED_FUNDERS"] = os.environ["ALLOWED_FUNDERS"]
    return shell([sys.executable, str(orch), "run", "field-targets-5", "--quiet"], env=env)


def run_battle_suite() -> dict[str, Any]:
    agent = ROOT / "bin" / "hexstrike-agent"
    if not agent.is_file():
        shell(["bash", str(AGENT_DIR / "build.sh")], cwd=AGENT_DIR)
    return shell([str(agent), "battle"])


def parse_battle_report() -> dict[str, Any]:
    path = ROOT / "artifacts" / "sandbox" / "battle-report.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def defense_score(attacks: dict[str, str], go_pass: bool) -> float:
    if not go_pass:
        return 0.0
    required = ("02-race-duplicate-sign", "04-replay-rescue-tx", "06-compromised-funder")
    if all(attacks.get(k) == "DEFENDED" for k in required):
        return 100.0
    defended = sum(1 for k in required if attacks.get(k) == "DEFENDED")
    return round(100.0 * defended / len(required), 1)


def run_defense_session(run_n: int, monitor_duration: int) -> dict[str, Any]:
    run_id = uuid.uuid4().hex[:12]
    print(f"\n[DEFENSE {run_n}/5] run_id={run_id}")
    env_note = {
        "ARKHAM_API_KEY_set": bool(os.environ.get("ARKHAM_API_KEY")),
        "ALLOWED_FUNDERS": os.environ.get("ALLOWED_FUNDERS", ALLOWED_FUNDER),
    }

    t0 = time.perf_counter()
    gt = go_test_all()
    eng = go_engine_defense_cases()
    hot = go_hot_path_latency_ms()
    pipeline = run_field_pipeline()
    battle = run_battle_suite()
    battle_data = parse_battle_report()

    attacks = eng.get("attacks", {})
    score = defense_score(attacks, gt["exit_code"] == 0 and eng["exit_code"] == 0)

    bus_errors = []
    for blob in (gt.get("stderr", ""), eng.get("stderr", ""), pipeline.get("stderr", "")):
        if "panic" in blob.lower():
            bus_errors.append("panic_detected")
        if "fatal error: concurrent map" in blob.lower():
            bus_errors.append("concurrent_map")

    report = {
        "test_id": f"hexstrike_defense_stress_{run_n:02d}",
        "session": "defense",
        "run": run_n,
        "run_id": run_id,
        "mode": "DEFENSE_MAX",
        "started_at": utc_now(),
        "env": env_note,
        "overall_score": score,
        "wall_clock_sec": round(time.perf_counter() - t0, 2),
        "attacks": attacks,
        "go_test": "PASS" if gt["exit_code"] == 0 else "FAIL",
        "engine_test": "PASS" if eng["exit_code"] == 0 else "FAIL",
        "hot_path": hot,
        "pipeline": {
            "success": pipeline["exit_code"] == 0,
            "elapsed_sec": pipeline["elapsed_sec"],
            "latency_ms": round(pipeline["elapsed_sec"] * 1000, 1),
        },
        "battle": {
            "exit_code": battle["exit_code"],
            "readiness_score": battle_data.get("summary", {}).get("readiness_score"),
            "elapsed_sec": battle["elapsed_sec"],
        },
        "bus": {"panics": bus_errors, "clean": len(bus_errors) == 0},
        "monitor_duration_config": monitor_duration,
    }
    report["finished_at"] = utc_now()

    out = ROOT / f"test_report_defense_{run_n:02d}.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"  score={score} pipeline={pipeline['elapsed_sec']}s hot_path={hot.get('latency_ms_hot_path')}ms")
    return report


def run_attack_session(run_n: int, recon_ip: str, monitor_duration: int) -> dict[str, Any]:
    run_id = uuid.uuid4().hex[:12]
    print(f"\n[ATTACK {run_n}/5] run_id={run_id} ip={recon_ip}")

    t0 = time.perf_counter()

    # Recon / attack surface (read-only)
    stress = shell(
        [
            sys.executable,
            str(ROOT / "scripts" / "stress_test.py"),
            "--target",
            VICTIM,
            "--ip",
            recon_ip,
            "--monitor-duration",
            str(min(monitor_duration, 30)),
        ],
    )

    amount_sim = shell([sys.executable, str(ROOT / "scripts" / "sandbox" / "run-amount-simulation-benchmark.py")],
                       env={"SIM_RUNS": "1"})

    gt = go_test_all()
    fees = shell(["go", "test", "./internal/tx/", "-run", "TestCalculateAggressiveFees", "-count=1"], cwd=AGENT_DIR)
    gate = shell(["go", "test", "./internal/entity/", "-run", "TestEntityGate", "-count=1"], cwd=AGENT_DIR)

    stress_data = {}
    sr = ROOT / "test_report_2026-07-10.json"
    if sr.is_file():
        try:
            stress_data = json.loads(sr.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    amount_ok = amount_sim["exit_code"] == 0
    fees_ok = fees["exit_code"] == 0
    gate_ok = gate["exit_code"] == 0
    components = [amount_ok, fees_ok, gate_ok, gt["exit_code"] == 0]
    score = round(100.0 * sum(components) / len(components), 1)

    report = {
        "test_id": f"hexstrike_attack_stress_{run_n:02d}",
        "session": "attack",
        "run": run_n,
        "run_id": run_id,
        "mode": "ATTACK_SIMULATION",
        "recon_ip": recon_ip,
        "started_at": utc_now(),
        "overall_score": score,
        "wall_clock_sec": round(time.perf_counter() - t0, 2),
        "stress_test": {
            "exit_code": stress["exit_code"],
            "overall_score": stress_data.get("overall_score"),
            "elapsed_sec": stress["elapsed_sec"],
        },
        "amount_simulation": {"pass": amount_ok, "elapsed_sec": amount_sim["elapsed_sec"]},
        "fees1559": {"pass": fees_ok, "elapsed_sec": fees["elapsed_sec"]},
        "entity_gate": {"pass": gate_ok, "elapsed_sec": gate["elapsed_sec"]},
        "go_test": "PASS" if gt["exit_code"] == 0 else "FAIL",
        "hot_path": {
            "pipeline_latency_ms": round(stress["elapsed_sec"] * 1000, 1),
            "amount_sim_ms": round(amount_sim["elapsed_sec"] * 1000, 1),
        },
        "monitor_duration_config": monitor_duration,
        "finished_at": utc_now(),
    }

    out = ROOT / f"test_report_attack_{run_n:02d}.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"  score={score} stress={stress['elapsed_sec']}s amount_sim={amount_ok}")
    return report


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Battle stress sessions (5 defense + 5 attack)")
    p.add_argument("--mode", choices=("defense", "attack", "both"), default="both")
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--ip", default=RECON_IP)
    p.add_argument("--monitor-duration", type=int, default=60)
    args = p.parse_args()

    if not os.environ.get("ALLOWED_FUNDERS"):
        os.environ["ALLOWED_FUNDERS"] = ALLOWED_FUNDER

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "generated_at": utc_now(),
        "runs_per_session": args.runs,
        "monitor_duration": args.monitor_duration,
        "defense": [],
        "attack": [],
    }

    if args.mode in ("defense", "both"):
        print("=" * 60)
        print("SESSION 1: DEFENSE (5×)")
        print("=" * 60)
        for i in range(1, args.runs + 1):
            summary["defense"].append(run_defense_session(i, args.monitor_duration))

    if args.mode in ("attack", "both"):
        print("=" * 60)
        print("SESSION 2: ATTACK (5×)")
        print("=" * 60)
        for i in range(1, args.runs + 1):
            summary["attack"].append(run_attack_session(i, args.ip, args.monitor_duration))

    def _avg_pipeline_sec(rows: list[dict]) -> float | None:
        vals = [r.get("pipeline", {}).get("elapsed_sec") for r in rows]
        nums = [v for v in vals if isinstance(v, (int, float))]
        return round(sum(nums) / len(nums), 2) if nums else None

    summary["defense_avg_score"] = (
        round(sum(r["overall_score"] for r in summary["defense"]) / len(summary["defense"]), 1)
        if summary["defense"]
        else None
    )
    summary["attack_avg_score"] = (
        round(sum(r["overall_score"] for r in summary["attack"]) / len(summary["attack"]), 1)
        if summary["attack"]
        else None
    )
    summary["defense_avg_pipeline_sec"] = _avg_pipeline_sec(summary["defense"])
    summary["go_test_final"] = go_test_all()
    summary["go_test_pass"] = summary["go_test_final"]["exit_code"] == 0

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("\n" + "=" * 60)
    print("BATTLE STRESS SUMMARY")
    print(json.dumps({
        "defense_avg_score": summary["defense_avg_score"],
        "attack_avg_score": summary["attack_avg_score"],
        "go_test_pass": summary["go_test_pass"],
        "summary_path": str(SUMMARY_PATH),
    }, indent=2))

    all_defense_100 = all(r.get("overall_score") == 100.0 for r in summary["defense"]) if summary["defense"] else True
    go_ok = summary["go_test_pass"]
    return 0 if all_defense_100 and go_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
