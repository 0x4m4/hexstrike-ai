#!/usr/bin/env python3
"""
Amount simulation benchmark — small vs large balances on BSC fork (DRY_RUN).

20 runs per scenario on real target addresses from field-targets-5.json.
No mainnet broadcasts; balances are injected via anvil_setBalance on local fork only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = Path(__file__).resolve().parent
EVENTS = ROOT / "artifacts" / "sandbox" / "dummy-bot-events.jsonl"
REPORT_JSON = ROOT / "artifacts" / "sandbox" / "amount-simulation-benchmark.json"
REPORT_MD = ROOT / "artifacts" / "sandbox" / "amount-simulation-analysis.md"
RUNS = int(os.environ.get("SIM_RUNS", "20"))

THRESHOLD_WEI = 500_000_000_000_000_000   # 0.5 ETH
MIN_GAS_WEI = 10_000_000_000_000_000      # 0.01 ETH
RESTORE_WEI = 100_000_000_000_000_000_000  # 100 ETH — reset between runs


@dataclass(frozen=True)
class Scenario:
    name: str
    balance_wei: int
    balance_eth: str
    expect: str
    category: str  # small | large
    note: str


SCENARIOS: list[Scenario] = [
    Scenario(
        "small_trigger",
        300_000_000_000_000_000,
        "0.3",
        "signed",
        "small",
        "Below THRESHOLD 0.5 ETH — rescue trigger, dry-run sign path",
    ),
    Scenario(
        "micro_no_gas",
        1_000_000_000_000_000,
        "0.001",
        "blocked_no_gas",
        "small",
        "Below threshold but < MIN_GAS 0.01 ETH — blocked",
    ),
    Scenario(
        "boundary_small",
        499_000_000_000_000_000,
        "0.499",
        "signed",
        "small",
        "Just under threshold — edge trigger",
    ),
    Scenario(
        "boundary_large",
        501_000_000_000_000_000,
        "0.501",
        "none",
        "large",
        "Just above threshold — no trigger",
    ),
    Scenario(
        "large_idle",
        10_000_000_000_000_000_000,
        "10.0",
        "none",
        "large",
        "Well above threshold — bot idle",
    ),
    Scenario(
        "large_max",
        100_000_000_000_000_000_000,
        "100.0",
        "none",
        "large",
        "Maximum test balance — no trigger",
    ),
]


def shell(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False, **kw)


def wei_hex(wei: int) -> str:
    return hex(wei)


def load_targets() -> list[dict]:
    path = SANDBOX / "field-targets-5.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("wallets", [])


def ensure_fork() -> dict[str, str]:
    env = {**os.environ, "ORCHESTRATOR_WORKFLOW": "field-targets-5"}
    shell(["python3", str(SANDBOX / "generate-target-profile.py")], env=env)
    proc = shell(["bash", str(SANDBOX / "setup-real-target-fork.sh")], env=env)
    if proc.returncode != 0:
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise SystemExit(1)

    out: dict[str, str] = {}
    env_file = SANDBOX / "anvil.env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def set_balance(address: str, wei: int, rpc: str) -> None:
    shell(["cast", "rpc", "anvil_setBalance", address, wei_hex(wei), "--rpc-url", rpc])


def event_count() -> int:
    if not EVENTS.is_file():
        return 0
    return len(EVENTS.read_text().splitlines())


def last_poll_event(since: int) -> dict | None:
    if not EVENTS.is_file():
        return None
    for line in reversed(EVENTS.read_text().splitlines()[since:]):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("event") == "poll":
            return d
    return None


def run_simulation(
    *,
    target: dict,
    scenario: Scenario,
    run_n: int,
    rpc: str,
    base_env: dict[str, str],
) -> dict:
    addr = target["address"]
    role = target["role"]
    since = event_count()

    set_balance(addr, RESTORE_WEI, rpc)
    time.sleep(0.15)
    set_balance(addr, scenario.balance_wei, rpc)
    time.sleep(0.15)

    env = {
        **base_env,
        "BOT_ADDRESS": addr,
        "RPC_URL": rpc,
        "DIRECT_RPC_URL": rpc,
        "DRY_RUN": "true",
        "HARDENING_ENABLED": "true",
        "CHAIN_ID": "56",
        "SANDBOX_ENV": str(SANDBOX / "anvil.env"),
    }
    started = time.time()
    proc = shell([sys.executable, str(SANDBOX / "dummy_bot.py"), "--once", "--dry-run"], env=env)
    elapsed = round(time.time() - started, 3)

    ev = last_poll_event(since) or {}
    action = ev.get("action", "no_event")
    result = ev.get("result") or action
    balance_wei = ev.get("balance_wei")

    ok = False
    if scenario.expect == "signed":
        ok = action == "trigger" and result == "signed"
    elif scenario.expect == "none":
        ok = action == "none"
    else:
        ok = result == scenario.expect

    return {
        "run": run_n,
        "role": role,
        "address": addr,
        "scenario": scenario.name,
        "category": scenario.category,
        "balance_wei": scenario.balance_wei,
        "balance_eth": scenario.balance_eth,
        "expected": scenario.expect,
        "action": action,
        "result": result,
        "pass": ok,
        "elapsed_sec": elapsed,
        "bot_exit": proc.returncode,
        "rescue_value_wei": int(base_env.get("RESCUE_VALUE_WEI", "1000000000000000000")),
        "would_rescue_eth": int(base_env.get("RESCUE_VALUE_WEI", "1000000000000000000")) / 1e18,
        "dry_run": True,
        "note": scenario.note,
    }


def analyze(results: list[dict]) -> dict:
    by_scenario: dict[str, list[dict]] = {}
    for r in results:
        by_scenario.setdefault(r["scenario"], []).append(r)

    scenario_stats = {}
    for name, rows in by_scenario.items():
        passed = sum(1 for r in rows if r["pass"])
        results_counter = Counter(r["result"] for r in rows)
        scenario_stats[name] = {
            "runs": len(rows),
            "passed": passed,
            "failed": len(rows) - passed,
            "pass_rate_pct": round(100 * passed / len(rows), 1) if rows else 0,
            "category": rows[0]["category"],
            "balance_eth": rows[0]["balance_eth"],
            "expected": rows[0]["expected"],
            "result_distribution": dict(results_counter),
            "avg_elapsed_sec": round(sum(r["elapsed_sec"] for r in rows) / len(rows), 3),
        }

    small_rows = [r for r in results if r["category"] == "small"]
    large_rows = [r for r in results if r["category"] == "large"]
    small_pass = sum(1 for r in small_rows if r["pass"])
    large_pass = sum(1 for r in large_rows if r["pass"])

    return {
        "small_category": {
            "runs": len(small_rows),
            "passed": small_pass,
            "pass_rate_pct": round(100 * small_pass / len(small_rows), 1) if small_rows else 0,
            "scenarios": [s.name for s in SCENARIOS if s.category == "small"],
        },
        "large_category": {
            "runs": len(large_rows),
            "passed": large_pass,
            "pass_rate_pct": round(100 * large_pass / len(large_rows), 1) if large_rows else 0,
            "scenarios": [s.name for s in SCENARIOS if s.category == "large"],
        },
        "per_scenario": scenario_stats,
        "total_pass": sum(1 for r in results if r["pass"]),
        "total_fail": sum(1 for r in results if not r["pass"]),
        "stable": all(s["pass_rate_pct"] == 100 for s in scenario_stats.values()),
    }


def write_markdown(report: dict) -> None:
    a = report["analysis"]
    lines = [
        "# Amount simulation analysis (fork DRY_RUN)",
        "",
        f"Generated: {report['generated_at']}",
        f"Mode: {report['mode']}",
        f"Runs per scenario: {report['runs_per_scenario']}",
        f"Targets: {', '.join(report['target_roles'])}",
        "",
        "## Parameters",
        "",
        f"| Param | Value |",
        f"|-------|-------|",
        f"| THRESHOLD_WEI | {THRESHOLD_WEI} (0.5 ETH) |",
        f"| MIN_GAS_WEI | {MIN_GAS_WEI} (0.01 ETH) |",
        f"| RESCUE_VALUE (fork) | {report['rescue_value_eth']} ETH (simulated, not broadcast) |",
        f"| Chain | BSC fork chain_id=56 |",
        "",
        "## Summary",
        "",
        f"- **Small amounts** ({a['small_category']['runs']} runs): "
        f"{a['small_category']['passed']}/{a['small_category']['runs']} pass "
        f"({a['small_category']['pass_rate_pct']}%)",
        f"- **Large amounts** ({a['large_category']['runs']} runs): "
        f"{a['large_category']['passed']}/{a['large_category']['runs']} pass "
        f"({a['large_category']['pass_rate_pct']}%)",
        f"- **Total**: {a['total_pass']}/{report['total_runs']} pass",
        f"- **Stable across runs**: {a['stable']}",
        "",
        "## Per-scenario (20 runs each)",
        "",
        "| Scenario | Category | Balance | Expected | Pass | Avg time |",
        "|----------|----------|---------|----------|------|----------|",
    ]
    for name, s in a["per_scenario"].items():
        lines.append(
            f"| {name} | {s['category']} | {s['balance_eth']} ETH | {s['expected']} | "
            f"{s['passed']}/{s['runs']} ({s['pass_rate_pct']}%) | {s['avg_elapsed_sec']}s |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "### Small balances",
        "- **0.3 / 0.499 ETH**: balance below 0.5 ETH threshold → bot **triggers** rescue path.",
        "  In fork watch mode (`DRY_RUN=true`, no private key) → result `signed` means "
        "**would sign**; no funds move on mainnet.",
        "- **0.001 ETH**: trigger fires but **blocked_no_gas** (< 0.01 ETH MIN_GAS).",
        "",
        "### Large balances",
        "- **0.501 / 10 / 100 ETH**: above threshold → **none** (bot idle, no rescue attempt).",
        "",
        "### Rescue amount (if signing were enabled)",
        f"- Configured `RESCUE_VALUE_WEI` on fork = **{report['rescue_value_eth']} ETH** to FUNDER — "
        "lab simulation only; field runs never broadcast to BSC mainnet.",
        "",
        "## Constraints",
        "",
        "- Read-only on live BSC; balance injection only on local Anvil fork.",
        "- Real hot wallet private key never used.",
        "",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not __import__("shutil").which("cast"):
        print("[FAIL] cast required", file=sys.stderr)
        return 1

    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    EVENTS.write_text("")

    fork_env = ensure_fork()
    rpc = fork_env.get("RPC_URL", "http://127.0.0.1:8545")
    rescue_wei = int(fork_env.get("RESCUE_VALUE_WEI", "1000000000000000000"))

    targets = load_targets()
    sim_roles = ("hot_wallet", "authority", "infra_correlated_wallet")
    sim_targets = [t for t in targets if t.get("role") in sim_roles]
    if not sim_targets:
        sim_targets = [{"role": "hot_wallet", "address": fork_env.get("BOT_ADDRESS", "")}]

    print(f"=== AMOUNT SIMULATION BENCHMARK ({RUNS} runs × {len(SCENARIOS)} scenarios) ===")
    print(f"RPC: {rpc} | DRY_RUN=true | targets={len(sim_targets)}")
    print(f"THRESHOLD=0.5 ETH | MIN_GAS=0.01 ETH | RESCUE_VALUE={rescue_wei/1e18} ETH")
    print()

    results: list[dict] = []
    for run_n in range(1, RUNS + 1):
        for sc in SCENARIOS:
            target = sim_targets[0] if sc.category == "small" else sim_targets[min(1, len(sim_targets) - 1)]
            if sc.name == "large_max":
                target = sim_targets[0]
            row = run_simulation(
                target=target,
                scenario=sc,
                run_n=run_n,
                rpc=rpc,
                base_env=fork_env,
            )
            results.append(row)
            icon = "✓" if row["pass"] else "✗"
            print(
                f"  [{run_n:2}/{RUNS}] {sc.name:18} {target['role']:22} "
                f"{sc.balance_eth:>6} ETH → {row['result']:22} {icon}"
            )

    analysis = analyze(results)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "bsc_fork_dry_run",
        "runs_per_scenario": RUNS,
        "scenarios_count": len(SCENARIOS),
        "total_runs": len(results),
        "target_roles": [t["role"] for t in sim_targets],
        "rpc": rpc,
        "rescue_value_wei": rescue_wei,
        "rescue_value_eth": rescue_wei / 1e18,
        "threshold_wei": THRESHOLD_WEI,
        "min_gas_wei": MIN_GAS_WEI,
        "analysis": analysis,
        "results": results,
    }

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report)

    print()
    print("=== ANALYSIS ===")
    print(f"  Small:  {analysis['small_category']['passed']}/{analysis['small_category']['runs']} "
          f"({analysis['small_category']['pass_rate_pct']}%)")
    print(f"  Large:  {analysis['large_category']['passed']}/{analysis['large_category']['runs']} "
          f"({analysis['large_category']['pass_rate_pct']}%)")
    print(f"  Total:  {analysis['total_pass']}/{len(results)}")
    print(f"  JSON:   {REPORT_JSON}")
    print(f"  Report: {REPORT_MD}")
    return 0 if analysis["total_fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
