#!/usr/bin/env python3
"""
Benchmark: rescue/withdraw attempt WITH gas vs WITHOUT gas (10 runs each scenario).

LOCAL ANVIL ONLY — uses dummy_bot rescue tx (native ETH value to FUNDER).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = Path(__file__).resolve().parent
REPORT = ROOT / "artifacts" / "sandbox" / "withdraw-gas-benchmark.json"
EVENTS = ROOT / "artifacts" / "sandbox" / "dummy-bot-events.jsonl"
RUNS = int(os.environ.get("BENCHMARK_RUNS", "10"))


@dataclass
class Scenario:
    name: str
    balance_wei: int
    expect: str  # signed | blocked_no_gas | none


SCENARIOS = [
    Scenario("with_gas", 300_000_000_000_000_000, "signed"),      # 0.3 ETH — enough for gas
    Scenario("without_gas", 1_000_000_000_000_000, "blocked_no_gas"),  # 0.001 ETH < MIN_GAS 0.01
]


def shell(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False, **kw)


def ensure_anvil() -> str:
    # Use local dummy Anvil (not BSC fork) — need test private keys
    env_file = SANDBOX / "anvil.env"
    pid_fork = Path(os.environ.get("TMPDIR", "/tmp")) / "hexstrike-anvil-fork.pid"
    pid_plain = Path(os.environ.get("TMPDIR", "/tmp")) / "hexstrike-anvil.pid"
    for pf in (pid_fork, pid_plain):
        if pf.is_file():
            try:
                os.kill(int(pf.read_text().strip()), 15)
            except (OSError, ValueError):
                pass
            pf.unlink(missing_ok=True)
    time.sleep(0.5)

    if env_file.is_file():
        txt = env_file.read_text()
        pk = ""
        for line in txt.splitlines():
            if line.startswith("BOT_PRIVATE_KEY="):
                pk = line.split("=", 1)[1].strip()
                break
        if not pk:
            env_file.unlink(missing_ok=True)

    proc = shell(["bash", str(SANDBOX / "start-anvil.sh")])
    if proc.returncode != 0 and "already running" not in (proc.stdout + proc.stderr):
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise SystemExit(1)
    if not env_file.is_file():
        shell(["bash", str(SANDBOX / "setup-anvil-env.sh")])
    rpc = "http://127.0.0.1:8545"
    return rpc


def load_env() -> dict[str, str]:
    env = os.environ.copy()
    env_file = SANDBOX / "anvil.env"
    if not env_file.is_file():
        shell(["bash", str(SANDBOX / "setup-anvil-env.sh")])
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    env["HARDENING_ENABLED"] = "false"
    env["DRY_RUN"] = "false"
    env["POLL_INTERVAL_SEC"] = "1"
    env["RPC_URL"] = "http://127.0.0.1:8545"
    env["DIRECT_RPC_URL"] = "http://127.0.0.1:8545"
    env["CHAIN_ID"] = "31337"
    return env


def set_balance(bot: str, wei: int, rpc: str) -> None:
    hex_bal = hex(wei)
    shell(["cast", "rpc", "anvil_setBalance", bot, hex_bal, "--rpc-url", rpc])


def event_count_before() -> int:
    if not EVENTS.is_file():
        return 0
    return len(EVENTS.read_text().splitlines())


def last_event_result(since: int) -> dict | None:
    if not EVENTS.is_file():
        return None
    lines = EVENTS.read_text().splitlines()[since:]
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("event") == "poll" and d.get("action") in ("trigger", "none", "blocked"):
            return d
        if d.get("result"):
            return d
    return None


def run_once(scenario: Scenario, run_n: int, env: dict[str, str]) -> dict:
    rpc = env.get("RPC_URL", "http://127.0.0.1:8545")
    bot = env["BOT_ADDRESS"]
    before = event_count_before()

    set_balance(bot, 10_000_000_000_000_000_000, rpc)  # reset 10 ETH
    time.sleep(0.3)
    set_balance(bot, scenario.balance_wei, rpc)

    proc = shell(
        [sys.executable, str(SANDBOX / "dummy_bot.py"), "--once"],
        env=env,
    )

    time.sleep(0.5)
    ev = last_event_result(before)
    result = (ev or {}).get("result") or (ev or {}).get("action") or "no_event"
    balance_wei = (ev or {}).get("balance_wei")
    tx_hash = (ev or {}).get("tx_hash")
    ok = result == scenario.expect
    if scenario.expect == "signed" and result == "signed":
        ok = True
    elif scenario.expect == "blocked_no_gas" and result == "blocked_no_gas":
        ok = True

    return {
        "run": run_n,
        "scenario": scenario.name,
        "balance_wei": scenario.balance_wei,
        "expected": scenario.expect,
        "actual": result,
        "pass": ok,
        "tx_hash": tx_hash,
        "balance_at_poll": balance_wei,
        "bot_exit": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-300:],
    }


def main() -> int:
    if not shutil_which("cast"):
        print("[FAIL] cast required", file=sys.stderr)
        return 1

    rpc = ensure_anvil()
    env = load_env()
    env["RPC_URL"] = rpc

    if not env.get("BOT_ADDRESS") or not env.get("BOT_PRIVATE_KEY"):
        print("[FAIL] anvil.env missing BOT_ADDRESS/BOT_PRIVATE_KEY", file=sys.stderr)
        return 1

    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    # fresh events for this benchmark
    EVENTS.write_text("")

    print(f"=== WITHDRAW GAS BENCHMARK ({RUNS} runs × 2 scenarios) ===")
    print(f"Bot: {env['BOT_ADDRESS']}")
    print(f"RPC: {rpc}")
    print(f"MIN_GAS_WEI: {env.get('MIN_GAS_WEI', '10000000000000000')}")
    print()

    results: list[dict] = []
    for i in range(1, RUNS + 1):
        for sc in SCENARIOS:
            row = run_once(sc, i, env)
            results.append(row)
            icon = "✓" if row["pass"] else "✗"
            print(
                f"  [{i}/{RUNS}] {sc.name:14} expect={sc.expect:16} "
                f"actual={row['actual']:20} {icon}"
            )

    summary = {}
    for sc in SCENARIOS:
        rows = [r for r in results if r["scenario"] == sc.name]
        passed = sum(1 for r in rows if r["pass"])
        summary[sc.name] = {
            "runs": len(rows),
            "passed": passed,
            "failed": len(rows) - passed,
            "pass_rate": round(100 * passed / len(rows), 1) if rows else 0,
            "expected": sc.expect,
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_anvil_only",
        "runs_per_scenario": RUNS,
        "bot": env["BOT_ADDRESS"],
        "rpc": rpc,
        "scenarios": {s.name: {"balance_wei": s.balance_wei, "expect": s.expect} for s in SCENARIOS},
        "summary": summary,
        "total_pass": sum(s["passed"] for s in summary.values()),
        "total_fail": sum(s["failed"] for s in summary.values()),
        "results": results,
    }

    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print()
    print("=== SUMMARY ===")
    for name, s in summary.items():
        print(f"  {name}: {s['passed']}/{s['runs']} pass ({s['pass_rate']}%)")
    print(f"  TOTAL: {report['total_pass']}/{RUNS * len(SCENARIOS)}")
    print(f"Report: {REPORT}")
    return 0 if report["total_fail"] == 0 else 1


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


if __name__ == "__main__":
    raise SystemExit(main())
