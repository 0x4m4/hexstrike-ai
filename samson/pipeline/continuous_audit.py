"""Continuous audit pipeline: RAG payloads → emulation → guardrail → proxy verification."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.redteam.adversary_executor import AdversaryEmulationExecutor
from samson.redteam.financial_guardrail_deployer import FinancialGuardrailDeployer
from samson.redteam.schemas import (
    AdversaryTargetContext,
    ContinuousAuditRequest,
    ContinuousAuditResult,
    ContinuousAuditStepResult,
    FinancialGuardrailDeployRequest,
)
from samson.pipeline.rag_payload_loader import RagPayloadLoader

logger = logging.getLogger(__name__)


class ContinuousAuditPipeline:
    """
    Automated pipeline:
    RAG payloads → direct adversary execution → guardrail deploy on financial intercept
    → identical payload through active proxy → before/after security assertion.
    """

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._loader = RagPayloadLoader(self._settings)
        self._executor = AdversaryEmulationExecutor(self._settings)
        self._deployer = FinancialGuardrailDeployer(self._settings)

    async def close(self) -> None:
        self._loader.close()
        self._executor.close()
        await self._deployer.close_proxy()

    async def run(self, req: ContinuousAuditRequest) -> ContinuousAuditResult:
        run_id = req.run_id or await asyncio.to_thread(self._ensure_exercise_run, req)
        if req.run_id:
            await asyncio.to_thread(self._assert_run_approved, req.run_id)
        target = AdversaryTargetContext(
            target_id=uuid4(),
            target_endpoint=req.target_endpoint,
            interface_type=req.interface_type,
            auth_headers=req.auth_headers,
        )

        payloads, rag_meta = await asyncio.to_thread(
            self._loader.load,
            target_endpoint=str(req.target_endpoint),
            interface_type=req.interface_type,
            operator_id=req.operator_id,
            query=req.rag_query,
            top_k=req.rag_top_k,
        )

        steps: list[ContinuousAuditStepResult] = []
        breaches_logged = 0
        guardrails_deployed = 0
        proxy_verifications = 0
        proxy_blocks = 0

        for payload in payloads:
            step = await self._run_payload_step(req, target, payload, run_id)
            steps.append(step)

            if step.breach_verified:
                breaches_logged += 1
                logger.warning(
                    "BREACH verified execution=%s entities=%s",
                    step.execution_id,
                    step.intercepted_financial_entities,
                )

            if step.guardrail_deployed:
                guardrails_deployed += 1

            if step.proxy_verified:
                proxy_verifications += 1
                if step.after_action in {"drop", "hitl"}:
                    proxy_blocks += 1

        result = ContinuousAuditResult(
            request_id=req.request_id,
            run_id=run_id,
            target_endpoint=str(req.target_endpoint),
            interface_type=req.interface_type,
            operator_id=req.operator_id,
            payloads_executed=len(steps),
            breaches_logged=breaches_logged,
            guardrails_deployed=guardrails_deployed,
            proxy_verifications=proxy_verifications,
            proxy_blocks=proxy_blocks,
            rag_metadata=rag_meta,
            steps=steps,
            assertion_passed=self._assert_pipeline(steps),
            completed_at=datetime.now(timezone.utc),
        )

        if self._settings.audit_enabled:
            await asyncio.to_thread(
                self._audit.write_redteam_audit,
                request_id=req.request_id,
                tool="continuous_audit",
                operator_id=req.operator_id,
                action="run_pipeline",
                outcome="pass" if result.assertion_passed else "fail",
                payload_hash=sha256_payload(req.model_dump(mode="json")),
                duration_ms=0,
                run_id=run_id,
            )

        return result

    async def _run_payload_step(
        self,
        req: ContinuousAuditRequest,
        target: AdversaryTargetContext,
        payload,
        run_id: UUID,
    ) -> ContinuousAuditStepResult:
        request_id = uuid4()
        emulation = await asyncio.to_thread(
            self._executor.execute,
            target=target,
            payload=payload,
            operator_id=req.operator_id,
            run_id=run_id,
            request_id=request_id,
        )

        step = ContinuousAuditStepResult(
            payload_id=payload.payload_id,
            attack_vector=payload.attack_vector,
            execution_id=emulation.execution_id,
            breach_verified=emulation.vulnerability_verified,
            before_http_status=emulation.http_status_code,
            before_allowed=True,
            intercepted_financial_entities=emulation.intercepted_financial_entities,
            guardrail_deployed=False,
            proxy_verified=False,
        )

        if not emulation.intercepted_financial_entities and not self._has_financial_content(payload):
            return step

        try:
            deploy = await self._deployer.deploy_from_execution(
                FinancialGuardrailDeployRequest(
                    request_id=uuid4(),
                    execution_id=emulation.execution_id,
                    operator_id=req.operator_id,
                    run_id=run_id,
                    policy_profile=req.policy_profile,
                    upstream_base_url=self._resolve_upstream(str(req.target_endpoint)),
                )
            )
            step.guardrail_deployed = True
            step.deployment_id = deploy.deployment_id
            step.proxy_listen_url = deploy.listen_url

            proxy_result = await self._rerun_through_proxy(
                target_endpoint=str(req.target_endpoint),
                payload=payload,
                target=target,
                listen_host=self._settings.guardrail_proxy_host,
                listen_port=self._settings.guardrail_proxy_port,
            )
            step.after_http_status = proxy_result["status_code"]
            step.after_action = proxy_result["action"]
            step.proxy_verified = proxy_result["verified"]
            step.proxy_response = proxy_result.get("body", {})
        finally:
            await self._deployer.close_proxy()

        return step

    async def _rerun_through_proxy(
        self,
        *,
        target_endpoint: str,
        payload,
        target: AdversaryTargetContext,
        listen_host: str,
        listen_port: int,
    ) -> dict:
        parsed = urlparse(target_endpoint)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        body, content_type = AdversaryEmulationExecutor._build_request_body(target, payload)  # noqa: SLF001
        proxy_url = f"http://{listen_host}:{listen_port}{path}"
        headers = {
            **target.auth_headers,
            "Content-Type": content_type,
        }

        async with httpx.AsyncClient(timeout=self._settings.http_timeout_sec, follow_redirects=False) as client:
            if content_type == "application/json":
                response = await client.post(proxy_url, json=body, headers=headers)
            else:
                content = body.encode("utf-8") if isinstance(body, str) else body
                response = await client.post(proxy_url, content=content, headers=headers)

        action = "allow"
        verified = False
        body_json: dict = {}
        try:
            body_json = response.json()
        except json.JSONDecodeError:
            body_json = {"raw_text": response.text[:4000]}

        if response.status_code == 403:
            action = "drop"
            verified = True
        elif response.status_code == 202:
            action = "hitl"
            verified = True
        elif body_json.get("status") == "blocked":
            action = "drop"
            verified = True
        elif body_json.get("status") == "awaiting_operator_review":
            action = "hitl"
            verified = True

        return {
            "status_code": response.status_code,
            "action": action,
            "verified": verified,
            "body": body_json,
            "proxy_url": proxy_url,
        }

    def _ensure_exercise_run(self, req: ContinuousAuditRequest) -> UUID:
        run_id = uuid4()
        self._db.execute(
            """
            INSERT INTO exercise_runs (
                run_id, operator_id, scenario_id, project, environment, status, approved_at, metadata
            ) VALUES (
                :run_id, :operator_id, :scenario_id, :project, :environment, 'approved', NOW(), CAST(:metadata AS jsonb)
            )
            ON CONFLICT (run_id) DO NOTHING
            """,
            {
                "run_id": str(run_id),
                "operator_id": req.operator_id,
                "scenario_id": req.scenario_id,
                "project": self._settings.project,
                "environment": self._settings.environment,
                "metadata": json.dumps(
                    {
                        "pipeline": "continuous_audit",
                        "target_endpoint": str(req.target_endpoint),
                        "interface_type": req.interface_type,
                    }
                ),
            },
        )
        return run_id

    def _assert_run_approved(self, run_id: UUID) -> None:
        row = self._db.fetchone(
            "SELECT status FROM exercise_runs WHERE run_id = :run_id",
            {"run_id": str(run_id)},
        )
        if not row or row.get("status") != "approved":
            from samson.core.errors import ApprovalRequiredError

            raise ApprovalRequiredError("Exercise run not approved", run_id=str(run_id))

    @staticmethod
    def _resolve_upstream(target_endpoint: str) -> str:
        parsed = urlparse(target_endpoint)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def _has_financial_content(payload) -> bool:
        text = payload.raw_payload_data.lower()
        return any(token in text for token in ("iban", "payment", "stripe", "beneficiary", "merchant"))

    @staticmethod
    def _assert_pipeline(steps: list[ContinuousAuditStepResult]) -> bool:
        financial_steps = [
            s
            for s in steps
            if s.intercepted_financial_entities or s.guardrail_deployed
        ]
        if not financial_steps:
            return True
        return all(s.proxy_verified and s.after_action in {"drop", "hitl"} for s in financial_steps)
