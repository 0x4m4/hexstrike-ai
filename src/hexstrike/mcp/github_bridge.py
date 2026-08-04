"""mcp_github_bridge — GitHub webhook event ingestion (Cursor/bot activity)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.paths import ARTIFACTS_DIR


@dataclass
class GithubBridgeMcp:
    """Ingest GitHub webhook payloads and publish to ContextBus."""

    bus: ContextBus
    webhook_secret_env: str = "GITHUB_WEBHOOK_SECRET"
    inbox_dir: Path = field(default_factory=lambda: ARTIFACTS_DIR / "github" / "inbox")

    def verify_signature(self, payload: bytes, signature_header: str | None) -> bool:
        secret = os.environ.get(self.webhook_secret_env, "").encode("utf-8")
        if not secret or not signature_header:
            return False
        if not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature_header)

    def ingest_pull_request(self, payload: dict[str, Any], *, verified: bool = False) -> dict[str, Any]:
        pr = payload.get("pull_request") or {}
        record = self.ingest("pull_request", payload, verified=verified)
        record["pr_number"] = pr.get("number")
        record["pr_title"] = pr.get("title")
        record["pr_state"] = pr.get("state")
        self.bus.publish(
            "mcp.github.pull_request",
            {"number": record.get("pr_number"), "action": payload.get("action")},
            source="mcp_github_bridge",
        )
        return record

    def ingest_push(self, payload: dict[str, Any], *, verified: bool = False) -> dict[str, Any]:
        record = self.ingest("push", payload, verified=verified)
        record["ref"] = payload.get("ref")
        record["commits"] = len(payload.get("commits") or [])
        head = payload.get("head_commit") or {}
        record["head_sha"] = head.get("id")
        record["head_message"] = head.get("message")
        self.bus.publish(
            "mcp.github.push",
            {"ref": record.get("ref"), "commits": record.get("commits"), "sha": record.get("head_sha")},
            source="mcp_github_bridge",
        )
        return record

    def ingest(self, event_type: str, payload: dict[str, Any], *, verified: bool = False) -> dict[str, Any]:
        record = {
            "event_type": event_type,
            "received_at": datetime.now(tz=timezone.utc).isoformat(),
            "verified": verified,
            "action": payload.get("action"),
            "repository": (payload.get("repository") or {}).get("full_name"),
            "sender": (payload.get("sender") or {}).get("login"),
        }
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{record['received_at'].replace(':', '-')}_{event_type}.json"
        out = self.inbox_dir / fname
        out.write_text(json.dumps({"meta": record, "payload": payload}, indent=2) + "\n", encoding="utf-8")

        self.bus.publish(
            "mcp.github.event",
            {"event_type": event_type, "repo": record["repository"], "path": str(out)},
            source="mcp_github_bridge",
        )
        return record

    def poll_inbox(self, limit: int = 20) -> list[Path]:
        if not self.inbox_dir.is_dir():
            return []
        files = sorted(self.inbox_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return files[:limit]
