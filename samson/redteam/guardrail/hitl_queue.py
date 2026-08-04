"""Human-in-the-loop queue for guardrail interception events."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import Database
from samson.redteam.schemas import GuardrailPendingAction

logger = logging.getLogger(__name__)


class GuardrailHitlQueue:
    """Persists and resolves guardrail pending actions requiring operator approval."""

    def __init__(self, settings: SamsonSettings | None = None, db: Database | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = db or Database(self._settings)

    async def enqueue(
        self,
        *,
        deployment_id: UUID,
        operator_id: str,
        run_id: UUID | None,
        intercepted_ibans: list[str],
        request_body: str,
        request_path: str,
        reason: str,
    ) -> GuardrailPendingAction:
        pending_id = uuid4()
        body_hash = hashlib.sha256(request_body.encode("utf-8")).hexdigest()
        action = GuardrailPendingAction(
            pending_id=pending_id,
            deployment_id=deployment_id,
            operator_id=operator_id,
            run_id=run_id,
            status="awaiting_operator_review",
            intercepted_ibans=intercepted_ibans,
            request_body_hash=body_hash,
            request_path=request_path,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
        await asyncio.to_thread(self._insert, action)
        logger.warning(
            "Guardrail HITL pending_id=%s deployment=%s ibans=%s",
            pending_id,
            deployment_id,
            intercepted_ibans,
        )
        return action

    def _insert(self, action: GuardrailPendingAction) -> None:
        self._db.execute(
            """
            INSERT INTO guardrail_pending_actions (
                pending_id, deployment_id, operator_id, run_id, status,
                intercepted_ibans, request_body_hash, request_path, reason
            ) VALUES (
                :pending_id, :deployment_id, :operator_id, :run_id, :status,
                :intercepted_ibans, :request_body_hash, :request_path, :reason
            )
            """,
            {
                "pending_id": str(action.pending_id),
                "deployment_id": str(action.deployment_id),
                "operator_id": action.operator_id,
                "run_id": str(action.run_id) if action.run_id else None,
                "status": action.status,
                "intercepted_ibans": action.intercepted_ibans,
                "request_body_hash": action.request_body_hash,
                "request_path": action.request_path,
                "reason": action.reason,
            },
        )

    async def approve(self, pending_id: UUID, operator_note: str = "") -> GuardrailPendingAction:
        return await self._resolve(pending_id, status="approved", operator_note=operator_note)

    async def reject(self, pending_id: UUID, operator_note: str = "") -> GuardrailPendingAction:
        return await self._resolve(pending_id, status="rejected", operator_note=operator_note)

    async def _resolve(self, pending_id: UUID, *, status: str, operator_note: str) -> GuardrailPendingAction:
        row = await asyncio.to_thread(
            self._db.fetchone,
            "SELECT * FROM guardrail_pending_actions WHERE pending_id = :pending_id",
            {"pending_id": str(pending_id)},
        )
        if not row:
            raise ValueError(f"Pending action not found: {pending_id}")

        await asyncio.to_thread(
            self._db.execute,
            """
            UPDATE guardrail_pending_actions
            SET status = :status, operator_note = :operator_note, resolved_at = NOW()
            WHERE pending_id = :pending_id
            """,
            {"pending_id": str(pending_id), "status": status, "operator_note": operator_note},
        )
        return GuardrailPendingAction(
            pending_id=UUID(str(row["pending_id"])),
            deployment_id=UUID(str(row["deployment_id"])),
            operator_id=str(row["operator_id"]),
            run_id=UUID(str(row["run_id"])) if row.get("run_id") else None,
            status=status,
            intercepted_ibans=list(row.get("intercepted_ibans") or []),
            request_body_hash=str(row["request_body_hash"]),
            request_path=str(row["request_path"]),
            reason=str(row["reason"]),
            created_at=row["created_at"],
            operator_note=operator_note,
        )

    async def get(self, pending_id: UUID) -> GuardrailPendingAction | None:
        row = await asyncio.to_thread(
            self._db.fetchone,
            "SELECT * FROM guardrail_pending_actions WHERE pending_id = :pending_id",
            {"pending_id": str(pending_id)},
        )
        if not row:
            return None
        return GuardrailPendingAction(
            pending_id=UUID(str(row["pending_id"])),
            deployment_id=UUID(str(row["deployment_id"])),
            operator_id=str(row["operator_id"]),
            run_id=UUID(str(row["run_id"])) if row.get("run_id") else None,
            status=str(row["status"]),
            intercepted_ibans=list(row.get("intercepted_ibans") or []),
            request_body_hash=str(row["request_body_hash"]),
            request_path=str(row["request_path"]),
            reason=str(row["reason"]),
            created_at=row["created_at"],
            operator_note=str(row.get("operator_note") or ""),
        )
