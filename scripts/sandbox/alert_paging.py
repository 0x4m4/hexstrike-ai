"""Critical alert paging sink (webhook → Slack / PagerDuty Events v2).

Env:
  ALERT_PAGING_ENABLED=true|1
  ALERT_WEBHOOK_URL=https://...          (Slack incoming webhook, etc.)
  ALERT_PAGERDUTY_KEY=<integration-key>  (Events API v2 routing key)
  ALERT_PAGING_TIMEOUT_SEC=5
  ALERT_PAGING_SEVERITIES=critical,high

Delivery failures are logged to artifacts but do **not** suppress local jsonl.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PAGE_LOG = ROOT / "artifacts" / "ops" / "paging-delivery.jsonl"
PD_ENQUEUE = "https://events.pagerduty.com/v2/enqueue"

CRITICAL_KINDS = frozenset(
    {
        "rpc_mismatch",
        "direct_rpc_unavailable",
        "BLOCK_COMPROMISED_FUNDER",
        "post_sign_drift",
        "BLOCK_DIRECT_RPC_DOWN",
        "BLOCK_GUARD_BYPASS",
        "BLOCK_MAINNET_KEYS",
        "kill_switch",
        "value_cap",
        "paging_drill",
    }
)


def _enabled() -> bool:
    return os.getenv("ALERT_PAGING_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def _severities() -> set[str]:
    raw = os.getenv("ALERT_PAGING_SEVERITIES", "critical")
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


def _sink_configured() -> bool:
    return bool(os.getenv("ALERT_WEBHOOK_URL", "").strip() or os.getenv("ALERT_PAGERDUTY_KEY", "").strip())


def should_page(entry: dict[str, Any]) -> bool:
    if not _enabled() or not _sink_configured():
        return False
    sev = str(entry.get("severity", "")).lower()
    kind = str(entry.get("type") or entry.get("kind") or entry.get("alert") or "")
    if sev in _severities():
        return True
    if kind in CRITICAL_KINDS:
        return True
    if str(entry.get("critical", "")).lower() in ("1", "true", "yes"):
        return True
    return False


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "hexstrike-paging/1"},
        method="POST",
    )
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "url_host": urllib.parse.urlparse(url).netloc if url else "",
        "ok": False,
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            record["status"] = getattr(resp, "status", 200)
            record["ok"] = 200 <= int(record["status"]) < 300
            record["body_prefix"] = resp.read()[:200].decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        record["error"] = str(exc)
        record["ok"] = False
    return record


def page_alert(entry: dict[str, Any]) -> dict[str, Any]:
    """POST to Slack webhook and/or PagerDuty. Returns delivery record."""
    timeout = float(os.getenv("ALERT_PAGING_TIMEOUT_SEC", "5"))
    text = (
        f"[HexStrike CRITICAL] {entry.get('type') or entry.get('kind') or 'alert'}: "
        f"{entry.get('detail') or entry.get('reason') or entry}"
    )
    deliveries: list[dict[str, Any]] = []

    webhook = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if webhook:
        payload = {
            "text": text,
            "severity": entry.get("severity", "critical"),
            "source": "hexstrike",
            "ts": datetime.now(timezone.utc).isoformat(),
            "alert": entry,
        }
        deliveries.append({**_post_json(webhook, payload, timeout), "sink": "webhook"})

    pd_key = os.getenv("ALERT_PAGERDUTY_KEY", "").strip()
    if pd_key:
        pd_payload = {
            "routing_key": pd_key,
            "event_action": "trigger",
            "payload": {
                "summary": text[:1024],
                "severity": "critical",
                "source": "hexstrike",
                "custom_details": entry,
            },
        }
        deliveries.append({**_post_json(PD_ENQUEUE, pd_payload, timeout), "sink": "pagerduty"})

    ok = any(d.get("ok") for d in deliveries) if deliveries else False
    status = next((d.get("status") for d in deliveries if d.get("ok")), None)
    if status is None and deliveries:
        status = deliveries[0].get("status")
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "status": status,
        "alert_sent": ok,
        "webhook_status": status,
        "deliveries": deliveries,
    }
    try:
        PAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with PAGE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return record


def maybe_page(entry: dict[str, Any]) -> None:
    if should_page(entry):
        page_alert(entry)
