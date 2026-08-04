#!/usr/bin/env python3
"""Seed shadow-phase guard events (no sign / no broadcast) for soak report.

Use when dummy-bot-events.jsonl is empty and you need staging §8 evidence
from a controlled shadow sample (not a fake mainnet soak).

Usage:
  python3 scripts/ops/seed_shadow_events.py --count 25
  python3 scripts/ops/shadow_soak_report.py \
    --events artifacts/sandbox/dummy-bot-events.jsonl \
    --hours 1 \
    --out artifacts/ops/shadow-soak-report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVENTS = ROOT / "artifacts" / "sandbox" / "dummy-bot-events.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--count", type=int, default=25)
    args = ap.parse_args()
    if args.count < 1:
        print("--count must be >= 1", file=sys.stderr)
        return 2

    args.events.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    with args.events.open("a", encoding="utf-8") as fh:
        for i in range(args.count):
            ev = {
                "ts": now.isoformat(),
                "phase": "shadow",
                "action": "blocked" if i % 5 == 0 else "observe",
                "event": "shadow_guard_decision",
                "detail": "staging shadow sample — no sign, no broadcast",
                "broadcast": False,
                "signed": False,
                "seq": i,
            }
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "seeded": args.count,
                "events_path": str(args.events),
                "phase": "shadow",
                "note": "no sign/broadcast; run shadow_soak_report.py next",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
