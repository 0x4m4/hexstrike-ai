"""Execute adversary payloads against authorized target contexts with full audit trail."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import sha256_payload
from samson.core.errors import NetworkError, ScopeViolationError
from samson.core.http_client import AuditHttpContext, SamsonHttpClient
from samson.core.scope import ScopeEnforcer
from samson.rag.rag_oracle import RagOracle
from samson.rag.schemas import BuildBriefRequest, RetrieveContextRequest
from samson.redteam.emulation_store import EmulationResultStore
from samson.redteam.entity_extractor import extract_financial_entities
from samson.redteam.schemas import (
    AdversaryEmulationResult,
    AdversaryTargetContext,
    ExecutionPayload,
)

logger = logging.getLogger(__name__)

_VECTOR_VERIFICATION_HINTS = {
    "Indirect_Prompt_Injection": ("ignore previous", "system prompt", "jailbreak", "override"),
    "Adversarial_Noise": ("misclassif", "evade", "noise"),
    "Context_Bleed": ("secret", "api key", "password", "iban", "sk_", "token"),
}


class AdversaryEmulationExecutor:
    """Runs ExecutionPayload against AdversaryTargetContext via real HTTP; persists and indexes results."""

    def __init__(self, settings: SamsonSettings | None = None, *, database_url: str | None = None) -> None:
        if database_url:
            settings = SamsonSettings(database_url=database_url)
        self._settings = settings or get_settings()
        self._scope = ScopeEnforcer(self._settings)
        self._http = SamsonHttpClient(self._settings)
        self._store = EmulationResultStore(self._settings)
        self._rag = RagOracle(self._settings)

    def close(self) -> None:
        self._http.close()
        self._store.close()
        self._rag.close()

    def execute(
        self,
        *,
        target: AdversaryTargetContext,
        payload: ExecutionPayload,
        operator_id: str,
        run_id: UUID | None = None,
        request_id: UUID | None = None,
        http_method: str = "POST",
    ) -> AdversaryEmulationResult:
        request_id = request_id or uuid4()
        self._scope.assert_operator(operator_id, request_id=request_id)
        url = str(target.target_endpoint)
        self._scope.assert_url_in_scope(url, request_id=request_id)

        audit_ctx = AuditHttpContext(
            request_id=request_id,
            operator_id=operator_id,
            run_id=run_id,
            tool="adversary_emulation",
        )

        body, content_type = self._build_request_body(target, payload)
        headers = {
            **target.auth_headers,
            "Content-Type": content_type,
            "X-Samson-Payload-Id": str(payload.payload_id),
            "X-Samson-Attack-Vector": payload.attack_vector,
        }

        start = time.perf_counter()
        try:
            if content_type == "application/json":
                response = self._http.request(
                    http_method,
                    url,
                    json=body,
                    headers=headers,
                    audit=audit_ctx,
                    expected_status=tuple(range(100, 600)),
                )
            else:
                response = self._http.request(
                    http_method,
                    url,
                    content=body.encode("utf-8") if isinstance(body, str) else body,
                    headers=headers,
                    audit=audit_ctx,
                    expected_status=tuple(range(100, 600)),
                )
        except NetworkError as exc:
            result = AdversaryEmulationResult(
                execution_id=uuid4(),
                vulnerability_verified=False,
                http_status_code=int(exc.detail.context.get("status_code", 0)),
                response_payload={"error": exc.detail.message, "context": exc.detail.context},
                intercepted_financial_entities=[],
            )
            self._store.save(
                result=result,
                target=target,
                payload=payload,
                operator_id=operator_id,
                run_id=run_id,
                request_id=request_id,
            )
            self._rag_analyze(result, payload, operator_id, request_id)
            raise

        response_body = self._parse_response(response)
        entities = extract_financial_entities(response_body)
        verified = self._verify_vulnerability(payload.attack_vector, response_body, entities)

        result = AdversaryEmulationResult(
            execution_id=uuid4(),
            vulnerability_verified=verified,
            http_status_code=response.status_code,
            response_payload=response_body,
            intercepted_financial_entities=entities,
        )

        self._store.save(
            result=result,
            target=target,
            payload=payload,
            operator_id=operator_id,
            run_id=run_id,
            request_id=request_id,
        )
        self._rag_analyze(result, payload, operator_id, request_id)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "Adversary emulation %s completed in %dms verified=%s entities=%d",
            result.execution_id,
            elapsed_ms,
            verified,
            len(entities),
        )
        return result

    async def execute_async(
        self,
        *,
        target: AdversaryTargetContext,
        payload: ExecutionPayload,
        operator_id: str,
        run_id: UUID | None = None,
        request_id: UUID | None = None,
        http_method: str = "POST",
    ) -> AdversaryEmulationResult:
        """Async wrapper around synchronous HTTP execution (runs in thread pool)."""
        return await asyncio.to_thread(
            self.execute,
            target=target,
            payload=payload,
            operator_id=operator_id,
            run_id=run_id,
            request_id=request_id,
            http_method=http_method,
        )

    def _rag_analyze(
        self,
        result: AdversaryEmulationResult,
        payload: ExecutionPayload,
        operator_id: str,
        request_id: UUID,
    ) -> None:
        """Best-effort RAG post-analysis — must never abort network audit / guardrail deploy."""
        try:
            import os

            if os.environ.get("SAMSON_SKIP_RAG_ANALYZE", "").lower() in {"1", "true", "yes"}:
                logger.info("RAG analyze skipped via SAMSON_SKIP_RAG_ANALYZE execution=%s", result.execution_id)
                return
            query = (
                f"Explain adversary emulation result for attack vector {payload.attack_vector}. "
                f"Entities: {', '.join(result.intercepted_financial_entities) or 'none'}."
            )
            retrieval = self._rag.retrieve_context(
                RetrieveContextRequest(
                    request_id=uuid4(),
                    query=query,
                    environment=self._settings.environment,
                    project=self._settings.project,
                    operator_id=operator_id,
                    tags=["emulation_result", payload.attack_vector],
                    top_k=6,
                )
            )
            # Chat briefing is optional; never block proxy lifecycle on slow Ollama /api/chat.
            if os.environ.get("SAMSON_SKIP_RAG_BRIEF", "1").lower() in {"1", "true", "yes"}:
                logger.info(
                    "RAG retrieve-only for execution=%s chunks=%s",
                    result.execution_id,
                    len(retrieval.chunks),
                )
                return
            self._rag.build_brief(
                BuildBriefRequest(
                    request_id=request_id,
                    retrieve_response=retrieval,
                    scenario_draft={
                        "attack_vector": payload.attack_vector,
                        "vulnerability_verified": result.vulnerability_verified,
                        "entities": result.intercepted_financial_entities,
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001 — audit loop continues without RAG briefing
            logger.warning(
                "RAG analyze skipped for execution=%s: %s",
                result.execution_id,
                exc,
            )

    @staticmethod
    def _build_request_body(target: AdversaryTargetContext, payload: ExecutionPayload) -> tuple[Any, str]:
        interface = target.interface_type.upper()
        raw = payload.raw_payload_data

        if interface == "REST-LLM-API":
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed, "application/json"
            except json.JSONDecodeError:
                pass
            return (
                {
                    "messages": [{"role": "user", "content": raw}],
                    "stream": False,
                },
                "application/json",
            )
        if interface in {"STRIPE-GATEWAY", "PLAID-INTEGRATION", "IBAN-PARSER"}:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed, "application/json"
            except json.JSONDecodeError:
                pass
            return {"payload": raw, "interface": target.interface_type}, "application/json"

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed, "application/json"
        except json.JSONDecodeError:
            pass
        return raw, "text/plain"

    @staticmethod
    def _parse_response(response: Any) -> dict[str, Any]:
        try:
            data = response.json()
            if isinstance(data, dict):
                return data
            return {"data": data}
        except json.JSONDecodeError:
            return {"raw_text": response.text[:16000]}

    @staticmethod
    def _verify_vulnerability(
        attack_vector: str,
        response_body: dict[str, Any],
        entities: list[str],
    ) -> bool:
        text = json.dumps(response_body, ensure_ascii=False).lower()
        hints = _VECTOR_VERIFICATION_HINTS.get(attack_vector, ())
        if entities:
            return True
        return any(hint in text for hint in hints)
