#!/usr/bin/env python3
"""Agent-Forensics-01 — полный analyzer (attack_chain + on-chain) после IOC-агента."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TASK_TO_KIND = {
    "run-analyzer-trx": "trx",
    "run-analyzer-evm": "evm",
    "run-analyzer-apeterminal": "apeterminal",
    "run-analyzer-solana": "solana",
    "run-analyzer-vanilla": "vanilla",
    "run-analyzer-permit": "permit",
    "run-analyzer-create2": "create2",
}

OUT_MAP = {
    "trx": "forensics/trx-drainer-report.json",
    "evm": "forensics/evm-drainer-report.json",
    "apeterminal": "forensics/apeterminal-drainer-report.json",
    "solana": "forensics/solana-drainer-report.json",
    "vanilla": "forensics/vanilla-drainer-report.json",
    "permit": "forensics/permit-farming-report.json",
    "create2": "forensics/create2-drainer-report.json",
}


def resolve_kind() -> str | None:
    if len(sys.argv) > 1 and sys.argv[1] in TASK_TO_KIND:
        return TASK_TO_KIND[sys.argv[1]]
    task = os.environ.get("HEXSTRIKE_TASK") or os.environ.get("ORCHESTRATOR_TASK")
    if task and task in TASK_TO_KIND:
        return TASK_TO_KIND[task]
    kind = os.environ.get("FORENSICS_ANALYZER_KIND")
    if kind:
        return kind
    for arg in sys.argv[1:]:
        if arg in TASK_TO_KIND.values():
            return arg
    return None


def main() -> int:
    kind = resolve_kind()
    if not kind:
        print(json.dumps({"success": False, "error": "unknown analyzer task", "hint": list(TASK_TO_KIND)}))
        return 1

    script = ROOT / "scripts" / "forensics" / "analyze.py"
    proc = subprocess.run([sys.executable, str(script), kind], cwd=str(ROOT))
    if proc.returncode != 0:
        print(json.dumps({"success": False, "agent": "Agent-Forensics-01", "kind": kind}))
        return 1

    out = ROOT / "artifacts" / OUT_MAP.get(kind, f"forensics/{kind}-report.json")
    instr_bytes = None
    if out.is_file():
        try:
            instr_bytes = json.loads(out.read_text(encoding="utf-8")).get("instruction_bytes")
        except json.JSONDecodeError:
            pass

    print(json.dumps({
        "success": True,
        "agent": "Agent-Forensics-01",
        "task": f"run-analyzer-{kind}",
        "kind": kind,
        "output": str(out),
        "instruction_bytes": instr_bytes,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
