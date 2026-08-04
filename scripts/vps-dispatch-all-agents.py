#!/usr/bin/env python3
"""Dispatch every agent task from agents/registry.json (VPS full run)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "agents" / "registry.json"
ORCH = ROOT / "scripts" / "hexstrike-orchestrator.py"
LOG_DIR = ROOT / "artifacts" / "orchestrator" / "all-agents-run"
SUMMARY = LOG_DIR / "summary.json"

# Skip MCP-only / deploy / local-mac-only tasks on VPS batch run
SKIP_TASKS = {
    ("Agent-Orchestrator", "dispatch"),
    ("Agent-Graph-01", "onchain-graph"),  # MCP manual
    ("Agent-Infra-01", "deploy-mcp"),
    ("Agent-Contract-02", "fetch-bytecode"),
    ("Agent-Report-06", "operator-crypto-audit"),  # mac operator lab
    ("Agent-Battle-07", "battle-suite"),  # needs anvil
    ("Agent-Battle-07", "redteam-all"),
}


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    agents = reg.get("agents", {})

    queue: list[tuple[str, str]] = []
    for agent, spec in agents.items():
        if agent == "Agent-Orchestrator":
            continue
        for task in (spec.get("tasks") or {}).keys():
            if (agent, task) in SKIP_TASKS:
                continue
            queue.append((agent, task))

    print(f"[all-agents] dispatching {len(queue)} tasks")
    results: list[dict] = []
    ok_n = fail_n = 0

    for i, (agent, task) in enumerate(queue, 1):
        log_file = LOG_DIR / f"{i:03d}-{agent}-{task}.log"
        print(f"  [{i}/{len(queue)}] {agent} / {task}")
        proc = subprocess.run(
            [sys.executable, str(ORCH), "dispatch", agent, task, "--quiet"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        log_file.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        success = proc.returncode == 0
        if success:
            ok_n += 1
        else:
            fail_n += 1
        results.append({
            "agent": agent,
            "task": task,
            "success": success,
            "log": str(log_file.relative_to(ROOT)),
        })

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(queue),
        "ok": ok_n,
        "failed": fail_n,
        "results": results,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"success": fail_n == 0, "ok": ok_n, "failed": fail_n, "summary": str(SUMMARY)}, indent=2))
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
