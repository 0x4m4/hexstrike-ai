#!/usr/bin/env python3
"""Agent-DualMode-08 — Slither/Mythril/Echidna/Foundry dual-mode contract audit."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hexstrike.bus.context_bus import ContextBus
from hexstrike.skills.dual_mode_agent import DualModeAgent

TASK_TO_MODE = {
    "contract-audit-defense": "defense",
    "contract-audit-offense": "offense",
}

DEFAULT_CONTRACT = "scripts/sandbox/contracts/RevertOnWithdraw.sol"


def resolve_task() -> str | None:
    if len(sys.argv) > 1 and sys.argv[1] in TASK_TO_MODE:
        return sys.argv[1]
    task = os.environ.get("HEXSTRIKE_TASK") or os.environ.get("ORCHESTRATOR_TASK")
    return task if task in TASK_TO_MODE else None


def resolve_mode(task: str | None) -> str:
    if task and task in TASK_TO_MODE:
        return TASK_TO_MODE[task]
    return os.environ.get("HEXSTRIKE_MODE", "defense")


def resolve_contract() -> str:
    return (
        os.environ.get("DUAL_MODE_CONTRACT")
        or os.environ.get("CONTRACT")
        or DEFAULT_CONTRACT
    )


def emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def write_output(report: dict) -> Path | None:
    out_env = os.environ.get("OUTPUT")
    if not out_env:
        return None
    out_path = Path(out_env)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    task = resolve_task()
    mode = resolve_mode(task)

    parser = argparse.ArgumentParser(description="Dual-Mode contract agent")
    parser.add_argument("task_name", nargs="?", help="Registry task (contract-audit-defense|offense)")
    parser.add_argument("--contract", default=resolve_contract(), help="Path to .sol file or project root")
    parser.add_argument("--mode", default=mode)
    parser.add_argument("--poc-test", default=os.environ.get("DUAL_MODE_POC_TEST"))
    args = parser.parse_args()

    if args.task_name in TASK_TO_MODE:
        mode = TASK_TO_MODE[args.task_name]

    agent = DualModeAgent(bus=ContextBus())
    report = agent.analyze(args.contract, mode=mode, poc_test=args.poc_test)
    out_path = write_output(report)
    artifact = out_path or report.get("artifact")

    emit({
        "success": not report.get("blocked"),
        "agent": "Agent-DualMode-08",
        "task": task or f"contract-audit-{mode}",
        "output": str(artifact) if artifact else None,
        **report,
    })
    return 0 if not report.get("blocked") else 2


if __name__ == "__main__":
    raise SystemExit(main())
