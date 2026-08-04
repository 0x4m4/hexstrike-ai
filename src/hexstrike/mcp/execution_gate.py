"""mcp_execution_gate — human-in-the-loop approval bridge (PendingAction queue)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.core.execution.broadcaster import ExecutionBroadcaster
from hexstrike.paths import PENDING_ACTION


@dataclass
class ExecutionGateMcp:
    """PendingAction queue — operator must approve before broadcast."""

    bus: ContextBus
    broadcaster: ExecutionBroadcaster
    pending_path: Path = PENDING_ACTION

    def load_pending(self) -> dict[str, Any] | None:
        if not self.pending_path.is_file():
            return None
        try:
            return json.loads(self.pending_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def submit(self, tx: dict[str, Any], *, reason: str = "", severity: str = "WARN") -> dict[str, Any]:
        pending = {
            "status": "awaiting_operator_review",
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "severity": severity,
            "action": "broadcast_tx",
            "reason": reason,
            "transaction": tx,
        }
        pre = self.broadcaster.preflight(tx)
        pending["preflight"] = {
            "ok": pre.ok,
            "gas_estimate": pre.gas_estimate,
            "gas_price_wei": pre.gas_price_wei,
            "errors": pre.errors,
        }
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_path.write_text(json.dumps(pending, indent=2) + "\n", encoding="utf-8")
        self.bus.publish("mcp.execution.submitted", {"severity": severity}, source="mcp_execution_gate")
        return pending

    def approve(self, operator_note: str = "") -> dict[str, Any]:
        pending = self.load_pending()
        if not pending:
            return {"success": False, "error": "no_pending_action"}

        pending["status"] = "approved"
        pending["approved_at"] = datetime.now(tz=timezone.utc).isoformat()
        pending["operator_note"] = operator_note
        self.pending_path.write_text(json.dumps(pending, indent=2) + "\n", encoding="utf-8")
        self.bus.publish("mcp.execution.approved", {}, source="mcp_execution_gate")
        return {"success": True, "pending": pending}

    def reject(self, operator_note: str = "") -> dict[str, Any]:
        pending = self.load_pending() or {}
        pending["status"] = "rejected"
        pending["rejected_at"] = datetime.now(tz=timezone.utc).isoformat()
        pending["operator_note"] = operator_note
        self.pending_path.write_text(json.dumps(pending, indent=2) + "\n", encoding="utf-8")
        self.bus.publish("mcp.execution.rejected", {}, source="mcp_execution_gate")
        return {"success": True}

    def status(self) -> dict[str, Any]:
        pending = self.load_pending()
        return {
            "has_pending": pending is not None,
            "status": (pending or {}).get("status"),
            "path": str(self.pending_path),
        }
