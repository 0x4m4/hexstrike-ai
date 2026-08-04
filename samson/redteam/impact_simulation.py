"""Impact simulation against authorized arena targets (ADR-004)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ApprovalRequiredError, ScopeViolationError
from samson.core.http_client import AuditHttpContext, SamsonHttpClient
from samson.core.payloads import PayloadOrchestrator
from samson.core.scope import ScopeEnforcer
from samson.redteam.adversary_executor import AdversaryEmulationExecutor
from samson.redteam.schemas import ImpactSimulationRequest, ImpactSimulationResult

logger = logging.getLogger(__name__)

_PROFILE_PHASES = {
    "persistence": ["persistence_marker"],
    "data_access": ["fixture_read"],
    "lateral_movement": ["service_discovery", "adjacent_probe"],
    "full_chain": ["persistence_marker", "fixture_read", "service_discovery", "adjacent_probe"],
    "financial_impact": ["financial_fixture_read"],
}


class ImpactSimulationAgent:
    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._scope = ScopeEnforcer(self._settings)
        self._http = SamsonHttpClient(self._settings)
        self._payloads = PayloadOrchestrator(self._settings, scope=self._scope, http=self._http)
        self._adversary = AdversaryEmulationExecutor(self._settings)
        self._audit_dir = Path("samson/redteam/impact/reports")
        self._audit_dir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self._payloads.close()
        self._adversary.close()
        self._http.close()

    def run(self, req: ImpactSimulationRequest) -> ImpactSimulationResult:
        if self._settings.require_human_approval:
            approval = self._load_approval(req.run_id)
            if approval.get("status") != "approved":
                raise ApprovalRequiredError(
                    "Impact simulation requires approved exercise run",
                    run_id=str(req.run_id),
                )

        self._scope.assert_operator(req.operator_id, request_id=req.request_id)
        target = self._scope.assert_target(req.arena_target_id, request_id=req.request_id)
        start = time.perf_counter()
        simulation_id = uuid4()

        phases = _PROFILE_PHASES.get(req.simulation_profile, [])
        payload_results: list[dict] = []
        emulation_results = []
        artifacts: list[str] = []

        if req.target_context and req.execution_payloads:
            for execution_payload in req.execution_payloads:
                emulation = self._adversary.execute(
                    target=req.target_context,
                    payload=execution_payload,
                    operator_id=req.operator_id,
                    run_id=req.run_id,
                    request_id=req.request_id,
                )
                emulation_results.append(emulation)
                payload_results.append(emulation.model_dump(mode="json"))

        for payload_id in req.payload_ids:
            result = self._payloads.execute(
                payload_id=payload_id,
                arena_target_id=req.arena_target_id,
                variables={**req.variables, "run_id": str(req.run_id), "scenario_id": req.scenario_id},
                operator_id=req.operator_id,
            )
            payload_results.append(result)

        for phase in phases:
            phase_result = self._execute_phase(phase, target.base_url, req)
            payload_results.append(phase_result)
            if phase_result.get("artifact_path"):
                artifacts.append(str(phase_result["artifact_path"]))

        impact_summary = self._summarize(payload_results, req.simulation_profile)
        audit_path = self._audit_dir / f"{simulation_id}.json"
        audit_path.write_text(json.dumps(payload_results, indent=2) + "\n", encoding="utf-8")

        self._db.execute(
            """
            INSERT INTO impact_simulations (
                simulation_id, run_id, operator_id, scenario_id, simulation_profile,
                phases_executed, synthetic_artifacts, atlas_technique_ids, reversible, audit_path
            ) VALUES (
                :simulation_id, :run_id, :operator_id, :scenario_id, :simulation_profile,
                :phases_executed, :synthetic_artifacts, :atlas_technique_ids, true, :audit_path
            )
            """,
            {
                "simulation_id": str(simulation_id),
                "run_id": str(req.run_id),
                "operator_id": req.operator_id,
                "scenario_id": req.scenario_id,
                "simulation_profile": req.simulation_profile,
                "phases_executed": phases,
                "synthetic_artifacts": artifacts,
                "atlas_technique_ids": req.atlas_techniques,
                "audit_path": str(audit_path),
            },
        )

        duration_ms = int((time.perf_counter() - start) * 1000)
        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=req.request_id,
                tool="impact_simulation",
                operator_id=req.operator_id,
                action="run",
                outcome="pass",
                payload_hash=sha256_payload(req.model_dump(mode="json")),
                duration_ms=duration_ms,
                run_id=req.run_id,
            )

        return ImpactSimulationResult(
            request_id=req.request_id,
            simulation_id=simulation_id,
            run_id=req.run_id,
            phases_executed=phases,
            synthetic_artifacts_accessed=artifacts,
            atlas_mappings=req.atlas_techniques,
            impact_summary=impact_summary,
            reversible=True,
            audit_path=str(audit_path),
            payload_results=payload_results,
            emulation_results=emulation_results,
            completed_at=datetime.now(tz=timezone.utc),
        )

    def _execute_phase(self, phase: str, base_url: str, req: ImpactSimulationRequest) -> dict:
        audit = AuditHttpContext(
            request_id=req.request_id,
            operator_id=req.operator_id,
            run_id=req.run_id,
            tool="impact_simulation",
            action=f"phase_{phase}",
        )
        if phase == "persistence_marker":
            url = f"{base_url}/api/v1/arena/markers"
            self._scope.assert_url_in_scope(url, request_id=req.request_id)
            return self._http.post_json(
                url,
                {
                    "marker_id": f"samson-{req.run_id}",
                    "scenario_id": req.scenario_id,
                    "phase": phase,
                },
                audit=audit,
            )
        if phase == "fixture_read":
            fixture = self._settings.fixture_root_path / "synthetic" / "credentials.json"
            if fixture.is_file():
                return {"phase": phase, "artifact_path": str(fixture), "status": "read"}
            url = f"{base_url}/api/v1/arena/fixtures/synthetic/credentials"
            self._scope.assert_url_in_scope(url, request_id=req.request_id)
            return {"phase": phase, "response": self._http.get_json(url, audit=audit)}
        if phase == "service_discovery":
            url = f"{base_url}/api/v1/arena/services"
            self._scope.assert_url_in_scope(url, request_id=req.request_id)
            return {"phase": phase, "response": self._http.get_json(url, audit=audit)}
        if phase == "adjacent_probe":
            url = f"{base_url}/api/v1/arena/adjacent/health"
            self._scope.assert_url_in_scope(url, request_id=req.request_id)
            return {"phase": phase, "response": self._http.get_json(url, audit=audit)}
        if phase == "financial_fixture_read":
            fixture = self._settings.fixture_root_path / "financial" / "synthetic_ibans.json"
            if fixture.is_file():
                return {"phase": phase, "artifact_path": str(fixture), "status": "read"}
            return {"phase": phase, "status": "missing_fixture", "path": str(fixture)}
        raise ScopeViolationError(f"Unknown impact phase: {phase}", request_id=req.request_id)

    def _load_approval(self, run_id: UUID) -> dict:
        row = self._db.fetchone(
            "SELECT status, metadata FROM exercise_runs WHERE run_id = :run_id",
            {"run_id": str(run_id)},
        )
        return row or {}

    @staticmethod
    def _summarize(results: list[dict], profile: str) -> str:
        return f"Impact simulation profile '{profile}' completed with {len(results)} phase/payload results."
