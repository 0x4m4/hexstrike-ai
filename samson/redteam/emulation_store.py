"""Persist adversary emulation results to PostgreSQL with pgvector embeddings."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import Database, vector_literal
from samson.core.http_client import OllamaClient
from samson.rag.search.ingest import DocumentIngester
from samson.redteam.schemas import AdversaryEmulationResult, AdversaryTargetContext, ExecutionPayload

logger = logging.getLogger(__name__)


class EmulationResultStore:
    """Writes emulation results to Postgres and indexes them for RAG Oracle retrieval."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._ollama = OllamaClient(self._settings)
        self._ingester = DocumentIngester(self._settings, self._db, self._ollama)

    def close(self) -> None:
        self._ingester.close()
        self._ollama.close()

    def save(
        self,
        *,
        result: AdversaryEmulationResult,
        target: AdversaryTargetContext,
        payload: ExecutionPayload,
        operator_id: str,
        run_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> UUID:
        response_text = json.dumps(result.response_payload, ensure_ascii=False)
        embedding = self._ollama.embed(response_text[:8000])
        self._write_artifact(result, target, payload, operator_id, run_id)
        rag_doc_id = self._index_for_rag(result, target, payload, operator_id)

        self._db.execute(
            """
            INSERT INTO adversary_emulation_results (
                execution_id, target_id, payload_id, run_id, request_id, operator_id,
                attack_vector, interface_type, http_status_code, vulnerability_verified,
                response_payload, intercepted_financial_entities, response_embedding,
                rag_document_id
            ) VALUES (
                :execution_id, :target_id, :payload_id, :run_id, :request_id, :operator_id,
                :attack_vector, :interface_type, :http_status_code, :vulnerability_verified,
                CAST(:response_payload AS jsonb), :intercepted_financial_entities,
                CAST(:response_embedding AS vector), :rag_document_id
            )
            ON CONFLICT (execution_id) DO UPDATE SET
                response_payload = EXCLUDED.response_payload,
                intercepted_financial_entities = EXCLUDED.intercepted_financial_entities,
                response_embedding = EXCLUDED.response_embedding,
                vulnerability_verified = EXCLUDED.vulnerability_verified,
                http_status_code = EXCLUDED.http_status_code
            """,
            {
                "execution_id": str(result.execution_id),
                "target_id": str(target.target_id),
                "payload_id": str(payload.payload_id),
                "run_id": str(run_id) if run_id else None,
                "request_id": str(request_id) if request_id else None,
                "operator_id": operator_id,
                "attack_vector": payload.attack_vector,
                "interface_type": target.interface_type,
                "http_status_code": result.http_status_code,
                "vulnerability_verified": result.vulnerability_verified,
                "response_payload": json.dumps(result.response_payload),
                "intercepted_financial_entities": result.intercepted_financial_entities,
                "response_embedding": vector_literal(embedding),
                "rag_document_id": str(rag_doc_id),
            },
        )
        logger.info("Persisted emulation result %s (rag_doc=%s)", result.execution_id, rag_doc_id)
        return rag_doc_id

    def _write_artifact(
        self,
        result: AdversaryEmulationResult,
        target: AdversaryTargetContext,
        payload: ExecutionPayload,
        operator_id: str,
        run_id: UUID | None,
    ) -> Path:
        out_dir = Path("samson/redteam/emulation/artifacts")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{result.execution_id}.json"
        path.write_text(
            json.dumps(
                {
                    "execution_id": str(result.execution_id),
                    "target_id": str(target.target_id),
                    "target_endpoint": str(target.target_endpoint),
                    "interface_type": target.interface_type,
                    "payload_id": str(payload.payload_id),
                    "attack_vector": payload.attack_vector,
                    "operator_id": operator_id,
                    "run_id": str(run_id) if run_id else None,
                    "http_status_code": result.http_status_code,
                    "vulnerability_verified": result.vulnerability_verified,
                    "response_payload": result.response_payload,
                    "intercepted_financial_entities": result.intercepted_financial_entities,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def _index_for_rag(
        self,
        result: AdversaryEmulationResult,
        target: AdversaryTargetContext,
        payload: ExecutionPayload,
        operator_id: str,
    ) -> UUID:
        rag_path = self._settings.rag_docs_path / "emulation" / f"{result.execution_id}.md"
        rag_path.parent.mkdir(parents=True, exist_ok=True)
        entities_lines = [f"- `{e}`" for e in result.intercepted_financial_entities] or ["_None_"]
        rag_path.write_text(
            "\n".join(
                [
                    f"# Adversary Emulation Result `{result.execution_id}`",
                    "",
                    f"- **Target:** `{target.target_endpoint}` ({target.interface_type})",
                    f"- **Attack vector:** {payload.attack_vector}",
                    f"- **Operator:** {operator_id}",
                    f"- **Vulnerability verified:** {result.vulnerability_verified}",
                    f"- **HTTP status:** {result.http_status_code}",
                    "",
                    "## Intercepted entities",
                    *entities_lines,
                    "",
                    "## Response payload",
                    "```json",
                    json.dumps(result.response_payload, indent=2, ensure_ascii=False),
                    "```",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return self._ingester.ingest_path(
            rag_path,
            doc_type="emulation_result",
            project=self._settings.project,
            environment=self._settings.environment,
            tags=["emulation_result", payload.attack_vector, target.interface_type],
            confidence=1.0 if result.vulnerability_verified else 0.5,
        )
