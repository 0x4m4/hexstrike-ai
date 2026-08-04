"""Arkham Intel client facade for Samson bulk-audit Web3 enrichment.

Official API: ``https://api.arkm.com`` with ``API-Key`` header
(see https://arkm.com/llms/guides/api-keys-authentication.md).
Persists into ``web3_recon_artifacts`` for the Shodan → Arkham → Audit pipeline.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import Database, sha256_payload
from samson.core.database import AuditRepository
from samson.redteam.arkham_collector import SamsonArkhamClient
from samson.redteam.schemas import ArkhamCollectResult

logger = logging.getLogger(__name__)

_EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Entity / label signals treated as outbound risk for guardrail blocking.
_RISK_ENTITY_TYPES = frozenset(
    {
        "mixer",
        "scam",
        "darknet",
        "ransomware",
        "sanction",
        "sanctioned",
        "theft",
        "hack",
        "phishing",
        "fraud",
        "tornado",
    }
)
_RISK_LABEL_FRAGMENTS = (
    "mixer",
    "tornado",
    "scam",
    "phishing",
    "drainer",
    "sanction",
    "stolen",
    "hack",
    "rug",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def classify_arkham_risk(payload: dict[str, Any] | None, *, artifact_entity_type: str | None = None,
                         artifact_label: str | None = None, artifact_entity_name: str | None = None) -> str:
    """Return risk tier: ``high`` | ``medium`` | ``low`` | ``unknown``."""
    entity_type = (artifact_entity_type or "").strip().lower()
    label = (artifact_label or "").strip().lower()
    name = (artifact_entity_name or "").strip().lower()
    blob = f"{entity_type} {label} {name}"
    if entity_type in _RISK_ENTITY_TYPES or any(frag in blob for frag in _RISK_LABEL_FRAGMENTS):
        return "high"
    if entity_type in {"cex", "dex", "bridge", "defi", "fund", "custodian"}:
        return "medium"
    if name or label:
        return "low"
    # Walk raw multi-chain payload if provided
    if isinstance(payload, dict):
        for value in payload.values() if not payload.get("arkhamEntity") else [payload]:
            if not isinstance(value, dict):
                continue
            ent = value.get("arkhamEntity") or {}
            lab = value.get("arkhamLabel") or {}
            et = str(ent.get("type") or "").lower()
            ln = str(lab.get("name") or ent.get("name") or "").lower()
            if et in _RISK_ENTITY_TYPES or any(frag in ln for frag in _RISK_LABEL_FRAGMENTS):
                return "high"
    return "unknown"


class ArkhamClient:
    """Thin async facade used by ``run-bulk-audit`` Web3 enrichment."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._inner = SamsonArkhamClient(self._settings)
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)

    async def close(self) -> None:
        await self._inner.close()

    async def fetch_address_data(
        self,
        address: str,
        *,
        operator_id: str = "operator-alpha",
        run_id: UUID | None = None,
        request_id: UUID | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """GET address intelligence; persist into ``web3_recon_artifacts``; return structured dict."""
        addr = (address or "").strip()
        if not _EVM_RE.match(addr):
            raise ValueError(f"Invalid EVM address: {address!r}")

        result: ArkhamCollectResult = await self._inner.lookup_address(
            addr,
            operator_id=operator_id,
            run_id=run_id,
            request_id=request_id,
            force_refresh=force_refresh,
            all_chains=True,
        )
        artifact = result.artifact
        risk = classify_arkham_risk(
            artifact.raw_payload if artifact else None,
            artifact_entity_type=artifact.entity_type if artifact else None,
            artifact_label=artifact.label_name if artifact else None,
            artifact_entity_name=artifact.entity_name if artifact else None,
        )
        row = {
            "artifact_id": str(artifact.artifact_id) if artifact else str(uuid4()),
            "request_id": str(result.request_id),
            "run_id": str(run_id) if run_id else None,
            "operator_id": operator_id,
            "address": addr,
            "risk_level": risk,
            "entity_name": artifact.entity_name if artifact else None,
            "entity_id": artifact.entity_id if artifact else None,
            "entity_type": artifact.entity_type if artifact else None,
            "label_name": artifact.label_name if artifact else None,
            "chains_seen": list(artifact.chains_seen) if artifact else [],
            "labels": list(artifact.labels) if artifact else [],
            "is_risk": risk == "high",
            "from_cache": result.from_cache,
            "raw_payload": artifact.raw_payload if artifact else {},
            "rag_doc_path": artifact.rag_doc_path if artifact else None,
            "collected_at": _utcnow().isoformat(),
        }
        await self._persist_web3_recon(row)
        logger.warning(
            "ArkhamClient address=%s risk=%s entity=%s label=%s cache=%s",
            addr,
            risk,
            row["entity_name"] or "-",
            row["label_name"] or "-",
            result.from_cache,
        )
        return row

    async def _persist_web3_recon(self, row: dict[str, Any]) -> None:
        import json

        def _write() -> None:
            self._db.execute(
                """
                INSERT INTO web3_recon_artifacts (
                    artifact_id, request_id, run_id, operator_id, address,
                    risk_level, is_risk, entity_name, entity_id, entity_type,
                    label_name, chains_seen, labels, from_cache, raw_payload,
                    rag_doc_path, collected_at
                ) VALUES (
                    :artifact_id, :request_id, :run_id, :operator_id, :address,
                    :risk_level, :is_risk, :entity_name, :entity_id, :entity_type,
                    :label_name, :chains_seen, :labels, :from_cache,
                    CAST(:raw_payload AS jsonb), :rag_doc_path, :collected_at
                )
                ON CONFLICT (artifact_id) DO UPDATE SET
                    risk_level = EXCLUDED.risk_level,
                    is_risk = EXCLUDED.is_risk,
                    entity_name = EXCLUDED.entity_name,
                    raw_payload = EXCLUDED.raw_payload,
                    collected_at = EXCLUDED.collected_at
                """,
                {
                    **row,
                    "raw_payload": json.dumps(row.get("raw_payload") or {}, ensure_ascii=False),
                },
            )
            if self._settings.audit_enabled:
                self._audit.write_redteam_audit(
                    request_id=UUID(row["request_id"]),
                    tool="arkham_client",
                    operator_id=row["operator_id"],
                    action="fetch_address_data",
                    outcome="pass",
                    payload_hash=sha256_payload(
                        {
                            "address": row["address"],
                            "risk_level": row["risk_level"],
                            "is_risk": row["is_risk"],
                        }
                    ),
                    duration_ms=0,
                    run_id=UUID(row["run_id"]) if row.get("run_id") else None,
                )

        import asyncio

        await asyncio.to_thread(_write)

    @staticmethod
    def extract_evm_addresses(text: str) -> list[str]:
        found = re.findall(r"0x[a-fA-F0-9]{40}", text or "")
        # Preserve order, dedupe case-insensitively
        seen: set[str] = set()
        out: list[str] = []
        for addr in found:
            key = addr.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(addr)
        return out
