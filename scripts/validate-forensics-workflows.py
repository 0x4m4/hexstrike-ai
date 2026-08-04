#!/usr/bin/env python3
"""Validate forensics workflows are registered inside workflows.workflows (not top-level)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "agents" / "workflows.json"

REQUIRED = [
    "trx-drainer-forensics",
    "evm-drainer-forensics",
    "apeterminal-forensics",
    "solana-drainer-forensics",
    "vanilla-drainer-forensics",
    "permit-farming-forensics",
    "create2-forensics",
]


def main() -> int:
    data = json.loads(WF.read_text(encoding="utf-8"))
    inner = data.get("workflows", {})
    missing = [w for w in REQUIRED if w not in inner]
    top_level = [w for w in REQUIRED if w in data and w not in inner]
    if top_level:
        print(f"WRONG NESTING (top-level keys): {top_level}")
        return 1
    if missing:
        print(f"STILL MISSING inside workflows: {missing}")
        return 1
    for w in REQUIRED:
        steps = inner[w].get("steps", [])
        if len(steps) < 2:
            print(f"TOO FEW STEPS for {w}: {len(steps)}")
            return 1
        if "agent" not in steps[0]:
            print(f"INVALID STEP FORMAT for {w}: {steps[:1]}")
            return 1
        # полный модуль: IOC + analyzer + report (3 шага)
        if len(steps) < 3:
            print(f"WARN: {w} has {len(steps)} steps (expected 3 for full module)")
    print("[INSPECTOR] All 7 forensics workflows registered correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
