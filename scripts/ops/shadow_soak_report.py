#!/usr/bin/env python3
"""Build §8 shadow soak evidence from dummy-bot event logs.

Usage:
  export GO_LIVE_PHASE=shadow
  # ... run bot ...
  python3 scripts/ops/shadow_soak_report.py \
    --events artifacts/sandbox/dummy-bot-events.jsonl \
    --hours 24 \
    --out artifacts/ops/shadow-soak-report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    s = str(raw).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=Path, required=True)
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--out", type=Path, default=Path("artifacts/ops/shadow-soak-report.json"))
    args = ap.parse_args()

    if not args.events.exists():
        print(f"missing events file: {args.events}", file=sys.stderr)
        report = {
            "result": "FAIL",
            "reason": "events_file_missing",
            "events_path": str(args.events),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    events: list[dict[str, Any]] = []
    sign_like = 0
    broadcast_like = 0
    blocked = 0
    for line in args.events.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _parse_ts(ev.get("ts") or ev.get("time") or ev.get("timestamp"))
        if ts is not None and ts < cutoff:
            continue
        events.append(ev)
        action = str(ev.get("action") or ev.get("event") or ev.get("type") or "").lower()
        if "sign" in action and "block" not in action:
            sign_like += 1
        if "broadcast" in action or "submit" in action or "sent" in action:
            broadcast_like += 1
        if "block" in action or action.startswith("block_"):
            blocked += 1

    # Shadow GO: events observed, no broadcast; sign should be zero (or only dry/blocked)
    ok = len(events) > 0 and broadcast_like == 0
    report = {
        "result": "PASS" if ok else "FAIL",
        "phase": "shadow",
        "window_hours": args.hours,
        "events_path": str(args.events),
        "events_in_window": len(events),
        "sign_like_events": sign_like,
        "broadcast_like_events": broadcast_like,
        "blocked_events": blocked,
        "no_broadcast": broadcast_like == 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "PASS requires events in window and zero broadcast-like actions",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
