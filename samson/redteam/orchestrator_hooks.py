"""Samson Orchestrator integration hooks for red-team modules."""

from __future__ import annotations

import logging
from uuid import UUID

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import Database
from samson.core.errors import ApprovalRequiredError
from samson.redteam.atlas.mapper import AtlasMapper
from samson.redteam.financial_guardrail import FinancialGuardrailAgent
from samson.redteam.financial_guardrail_deployer import FinancialGuardrailDeployer
from samson.redteam.financial_sandbox import FinancialSandboxAgent
from samson.redteam.garak.scanner import GarakScanner
from samson.redteam.impact_simulation import ImpactSimulationAgent
from samson.redteam.pyrit.risk_engine import PyRITRiskEngine
from samson.redteam.remediation_demo import RemediationDemonstrationAgent
from samson.redteam.schemas import (
    ATLASMapRequest,
    ATLASMapResult,
    FinancialGuardrailDeployRequest,
    FinancialGuardrailDeployResult,
    FinancialGuardrailRequest,
    FinancialGuardrailResult,
    FinancialSandboxRequest,
    FinancialSandboxResult,
    GarakScanRequest,
    GarakScanResult,
    ImpactSimulationRequest,
    ImpactSimulationResult,
    PyRITRiskRequest,
    PyRITRiskResult,
    RemediationDemoRequest,
    RemediationDemoResult,
)

logger = logging.getLogger(__name__)


class SamsonRedTeamHooks:
    """Production hook surface for Samson Orchestrator."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._pyrit = PyRITRiskEngine(self._settings)
        self._garak = GarakScanner(self._settings)
        self._atlas = AtlasMapper(self._settings)
        self._impact = ImpactSimulationAgent(self._settings)
        self._remediation = RemediationDemonstrationAgent(self._settings)
        self._financial = FinancialSandboxAgent(self._settings)
        self._financial_guardrail = FinancialGuardrailAgent(self._settings)
        self._guardrail_deployer = FinancialGuardrailDeployer(self._settings)

    def close(self) -> None:
        self._garak.close()
        self._impact.close()
        self._remediation.close()
        self._financial.close()
        self._financial_guardrail.close()
        try:
            import asyncio
            asyncio.run(self._guardrail_deployer.close())
        except RuntimeError:
            pass

    def evaluate_scenario_risk(self, req: PyRITRiskRequest) -> PyRITRiskResult:
        return self._pyrit.evaluate(req)

    def scan_model_health(self, req: GarakScanRequest) -> GarakScanResult:
        return self._garak.scan(req)

    def map_to_atlas(self, req: ATLASMapRequest) -> ATLASMapResult:
        return self._atlas.map_artifact(req)

    def run_impact_simulation(self, req: ImpactSimulationRequest) -> ImpactSimulationResult:
        pyrit = self._pyrit.evaluate(
            PyRITRiskRequest(
                request_id=req.request_id,
                scenario_id=req.scenario_id,
                scenario_draft={"profile": req.simulation_profile, "payload_ids": req.payload_ids},
                atlas_techniques=req.atlas_techniques,
                target_profile={"arena_target_id": req.arena_target_id},
                environment=req.environment,
                operator_id=req.operator_id,
            )
        )
        if pyrit.blocked:
            raise ApprovalRequiredError(
                "PyRIT blocked impact simulation",
                risk_score=pyrit.risk_score,
                risk_band=pyrit.risk_band,
            )
        return self._impact.run(req)

    def generate_remediation_demo(self, req: RemediationDemoRequest) -> RemediationDemoResult:
        return self._remediation.run(req)

    def deploy_guardrail_middleware(self, req: RemediationDemoRequest) -> RemediationDemoResult:
        req = req.model_copy(update={"demo_type": "guardrail_container"})
        return self._remediation.run(req)

    def run_financial_simulation(self, req: FinancialSandboxRequest) -> FinancialSandboxResult:
        pyrit = self._pyrit.evaluate(
            PyRITRiskRequest(
                request_id=req.request_id,
                scenario_id=req.scenario_id,
                scenario_draft={"technique": req.technique, "merchant": req.mock_merchant_id},
                environment=req.environment,
                operator_id=req.operator_id,
            )
        )
        if pyrit.blocked:
            raise ApprovalRequiredError("PyRIT blocked financial simulation", risk_score=pyrit.risk_score)
        return self._financial.run(req)

    def deploy_financial_guardrail(self, req: FinancialGuardrailRequest) -> FinancialGuardrailResult:
        return self._financial_guardrail.run(req)

    async def deploy_financial_guardrail_from_execution(
        self, req: FinancialGuardrailDeployRequest
    ) -> FinancialGuardrailDeployResult:
        return await self._guardrail_deployer.deploy_from_execution(req)

    def teardown_financial_guardrail(self, deployment_id: UUID, req: FinancialGuardrailRequest) -> FinancialGuardrailResult:
        teardown_req = req.model_copy(update={"action": "teardown"})
        return self._financial_guardrail.run(teardown_req)

    def assert_exercise_approved(self, run_id: UUID) -> None:
        row = self._db.fetchone(
            "SELECT status FROM exercise_runs WHERE run_id = :run_id",
            {"run_id": str(run_id)},
        )
        if not row or row.get("status") != "approved":
            raise ApprovalRequiredError("Exercise run not approved", run_id=str(run_id))
