"""Remediation demonstration and guardrail container deployment (ADR-004)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ApprovalRequiredError
from samson.core.http_client import SamsonHttpClient
from samson.core.scope import ScopeEnforcer
from samson.rag.rag_oracle import RagOracle
from samson.rag.schemas import WriteReportContextRequest
from samson.redteam.pyrit.risk_engine import PyRITRiskEngine
from samson.redteam.schemas import PyRITRiskRequest, RemediationDemoRequest, RemediationDemoResult

logger = logging.getLogger(__name__)


class RemediationDemonstrationAgent:
    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._scope = ScopeEnforcer(self._settings)
        self._http = SamsonHttpClient(self._settings)
        self._rag = RagOracle(self._settings)
        self._pyrit = PyRITRiskEngine(self._settings)

    def close(self) -> None:
        self._http.close()
        self._rag.close()

    def run(self, req: RemediationDemoRequest) -> RemediationDemoResult:
        if self._settings.require_human_approval:
            row = self._db.fetchone(
                "SELECT status FROM exercise_runs WHERE run_id = :run_id",
                {"run_id": str(req.run_id)},
            )
            if not row or row.get("status") != "approved":
                raise ApprovalRequiredError("Remediation demo requires approved run", run_id=str(req.run_id))

        self._scope.assert_operator(req.operator_id, request_id=req.request_id)
        start = time.perf_counter()
        demo_id = uuid4()
        guardrail_deployment_id: UUID | None = None
        pyrit_post_score: float | None = None

        if req.demo_type == "guardrail_container":
            guardrail_deployment_id = self._deploy_guardrail_container(req, demo_id)

        report = self._rag.write_report_context(
            WriteReportContextRequest(
                request_id=req.request_id,
                run_id=req.run_id,
                operator_id=req.operator_id,
                scenario_id=str(req.simulation_id or req.run_id),
                telemetry_summary={"demo_type": req.demo_type, "audience": req.audience},
                findings=[],
                remediation_notes=["guardrail deployment", "impact protection"],
            )
        )

        if req.demo_type == "guardrail_container":
            pyrit_result = self._pyrit.evaluate(
                PyRITRiskRequest(
                    request_id=uuid4(),
                    scenario_id=str(req.simulation_id or req.run_id),
                    scenario_draft={"title": "post-guardrail validation", "demo_type": req.demo_type},
                    environment=self._settings.environment,
                    operator_id=req.operator_id,
                )
            )
            pyrit_post_score = pyrit_result.risk_score

        self._db.execute(
            """
            INSERT INTO remediation_demos (
                demo_id, run_id, simulation_id, demo_type, report_id, audience, pyrit_post_score, summary
            ) VALUES (
                :demo_id, :run_id, :simulation_id, :demo_type, :report_id, :audience, :pyrit_post_score, :summary
            )
            """,
            {
                "demo_id": str(demo_id),
                "run_id": str(req.run_id),
                "simulation_id": str(req.simulation_id) if req.simulation_id else None,
                "demo_type": req.demo_type,
                "report_id": str(report.report_id),
                "audience": req.audience,
                "pyrit_post_score": pyrit_post_score,
                "summary": f"Remediation demo {req.demo_type} for audience {req.audience}",
            },
        )

        duration_ms = int((time.perf_counter() - start) * 1000)
        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=req.request_id,
                tool="remediation_demo",
                operator_id=req.operator_id,
                action=req.demo_type,
                outcome="pass",
                payload_hash=sha256_payload(req.model_dump(mode="json")),
                duration_ms=duration_ms,
                run_id=req.run_id,
            )

        return RemediationDemoResult(
            request_id=req.request_id,
            demo_id=demo_id,
            report_id=report.report_id,
            report_path=report.report_path,
            guardrail_deployment_id=guardrail_deployment_id,
            pyrit_post_score=pyrit_post_score,
            citations=[c.source_path for c in report.citations],
            completed_at=datetime.now(tz=timezone.utc),
        )

    def _deploy_guardrail_container(self, req: RemediationDemoRequest, demo_id: UUID) -> UUID:
        deployment_id = uuid4()
        deploy_url = f"{self._settings.arena_base_url_str}/api/v1/guardrail/deploy"
        self._scope.assert_url_in_scope(deploy_url, request_id=req.request_id)
        policy_rules = {
            "block_prompt_injection": True,
            "iban_allowlist_enforced": True,
            "max_transfer_eur": 10000,
            "require_operator_marker": True,
        }
        response = self._http.post_json(
            deploy_url,
            {
                "deployment_id": str(deployment_id),
                "namespace": self._settings.arena_namespace,
                "policy_profile": "strict",
                "policy_rules": policy_rules,
            },
        )
        self._db.execute(
            """
            INSERT INTO guardrail_deployments (
                deployment_id, demo_id, arena_namespace, policy_rules, status
            ) VALUES (
                :deployment_id, :demo_id, :arena_namespace, CAST(:policy_rules AS jsonb), 'active'
            )
            """,
            {
                "deployment_id": str(deployment_id),
                "demo_id": str(demo_id),
                "arena_namespace": self._settings.arena_namespace,
                "policy_rules": json.dumps(policy_rules),
            },
        )
        logger.info("Guardrail container deployed: %s response=%s", deployment_id, response)
        return deployment_id
