#!/usr/bin/env python3
"""Fire a synthetic critical alert to verify paging (Slack / PagerDuty).

Usage:
  export ALERT_PAGING_ENABLED=true
  export ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...
  # or: export ALERT_PAGERDUTY_KEY=<integration-key>
  python3 scripts/ops/paging_drill.py

After on-call ACKs:
  export PAGING_DRILL_ACK=true
  python3 scripts/ops/paging_drill.py --record-ack

Artifacts: artifacts/ops/paging-drill-<ts>.json
Schema (PASS): result, alert_sent, webhook_status, ack_received
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "sandbox"))

from alert_paging import page_alert, should_page  # noqa: E402
from balance_guard import append_alert  # noqa: E402

# Must NOT match paging-drill-YYYYMMDD…json glob (was causing --record-ack FAIL).
ACK_STATE = ROOT / "artifacts" / "ops" / "paging_ack_state.json"


def _ack_true() -> bool:
    if os.getenv("PAGING_DRILL_ACK", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    if ACK_STATE.exists():
        try:
            return bool(json.loads(ACK_STATE.read_text()).get("ack_received"))
        except (OSError, json.JSONDecodeError):
            return False
    return False


def _drill_artifacts(out_dir: Path) -> list[Path]:
    """Timestamped drills only: paging-drill-20260717T131518Z.json"""
    return sorted(
        p
        for p in out_dir.glob("paging-drill-*.json")
        if p.name != "paging-drill-ack.json" and p.stem.count("T") >= 1
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record-ack",
        action="store_true",
        help="Record on-call ACK (requires PAGING_DRILL_ACK=true) into latest drill artifact",
    )
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "artifacts" / "ops"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.record_ack:
        if os.getenv("PAGING_DRILL_ACK", "").strip().lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            print("Set PAGING_DRILL_ACK=true after on-call acknowledges the page", file=sys.stderr)
            return 2
        ACK_STATE.write_text(
            json.dumps(
                {"ack_received": True, "ts": datetime.now(timezone.utc).isoformat()},
                indent=2,
            )
            + "\n"
        )
        drills = _drill_artifacts(out_dir)
        if drills:
            latest = drills[-1]
            data = json.loads(latest.read_text())
            data["ack_received"] = True
            data["result"] = "PASS" if data.get("alert_sent") else data.get("result", "FAIL")
            data["verdict"] = data["result"]
            latest.write_text(json.dumps(data, indent=2) + "\n")
            print(json.dumps(data, indent=2))
            print(f"updated {latest}", file=sys.stderr)
            return 0 if data.get("result") == "PASS" else 1
        print(f"ack recorded → {ACK_STATE} (no drill json yet)", file=sys.stderr)
        return 0

    entry = {
        "type": "paging_drill",
        "severity": "critical",
        "kind": "paging_drill",
        "detail": f"hexstrike paging drill {ts}",
        "critical": True,
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    webhook = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    pd_key = os.getenv("ALERT_PAGERDUTY_KEY", "").strip()
    configured = bool(webhook or pd_key)

    append_alert(entry)
    delivery = page_alert(entry) if should_page(entry) else {"ok": False, "skipped": True, "status": None}
    alert_sent = bool(delivery.get("ok") or delivery.get("alert_sent"))
    webhook_status = delivery.get("webhook_status") or delivery.get("status")
    ack_received = _ack_true()

    if not configured:
        result = "SKIP_NO_CONFIG"
    elif alert_sent and ack_received:
        result = "PASS"
    elif alert_sent and not ack_received:
        result = "PASS_PENDING_ACK"
    else:
        result = "FAIL"

    report = {
        "result": result,
        "alert_sent": alert_sent,
        "webhook_status": webhook_status,
        "ack_received": ack_received,
        "ts": ts,
        "ALERT_PAGING_ENABLED": os.getenv("ALERT_PAGING_ENABLED", ""),
        "webhook_configured": bool(webhook),
        "pagerduty_configured": bool(pd_key),
        "should_page": should_page(entry),
        "delivery": delivery,
        "verdict": result,
        "note": "Set PAGING_DRILL_ACK=true && python3 scripts/ops/paging_drill.py --record-ack after on-call ACK",
    }

    path = out_dir / f"paging-drill-{ts}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

    if result == "FAIL":
        return 1
    if result == "SKIP_NO_CONFIG":
        print(
            "operator-owned: set ALERT_PAGING_ENABLED=true and ALERT_WEBHOOK_URL or ALERT_PAGERDUTY_KEY",
            file=sys.stderr,
        )
        return 2
    if result == "PASS_PENDING_ACK":
        print("alert sent — awaiting on-call ACK (PAGING_DRILL_ACK=true --record-ack)", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
