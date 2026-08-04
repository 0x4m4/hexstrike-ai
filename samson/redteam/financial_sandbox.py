"""Financial impact simulation via arena mock payment services (ADR-005).

Also exposes Web3 synthetic diversion signing (env ``SAMSON_WEB3_PRIVATE_KEY``)
through :mod:`samson.redteam.web3_gas_governor` when breaches are confirmed.
"""

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
from samson.core.http_client import AuditHttpContext, SamsonHttpClient
from samson.core.payloads import PayloadOrchestrator
from samson.core.scope import ScopeEnforcer
from samson.redteam.adversary_executor import AdversaryEmulationExecutor
from samson.redteam.atlas.mapper import AtlasMapper
from samson.redteam.schemas import ATLASMapRequest, FinancialSandboxRequest, FinancialSandboxResult
from samson.redteam.web3_gas_governor import DiversionResult, GasTransactionGovernor, get_gas_governor

logger = logging.getLogger(__name__)

_TECHNIQUE_PAYLOADS = {
    "invoice_substitution": "financial_invoice_substitution",
    "payment_api_abuse": "financial_payment_intent_abuse",
    "beneficiary_swap": "financial_beneficiary_swap",
    "llm_payment_injection": "financial_llm_payment_injection",
}


class FinancialSandboxAgent:
    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._scope = ScopeEnforcer(self._settings)
        self._http = SamsonHttpClient(self._settings)
        self._payloads = PayloadOrchestrator(self._settings, scope=self._scope, http=self._http)
        self._atlas = AtlasMapper(self._settings)
        self._adversary = AdversaryEmulationExecutor(self._settings)
        self._gas = get_gas_governor(self._settings)
        self._ledger_dir = Path("samson/redteam/financial/ledger")
        self._ledger_dir.mkdir(parents=True, exist_ok=True)

    @property
    def gas_governor(self) -> GasTransactionGovernor:
        return self._gas

    def close(self) -> None:
        self._payloads.close()
        self._adversary.close()
        self._http.close()

    def sign_breach_diversion(
        self,
        *,
        operator_id: str,
        run_id: UUID | None,
        request_id: UUID,
        execution_id: UUID,
        target_endpoint: str,
        vulnerability_verified: bool,
    ) -> DiversionResult | None:
        """On confirmed breach, sign one synthetic diversion within the gas ceiling."""
        if not vulnerability_verified:
            return None
        return self._gas.sign_synthetic_diversion_on_breach(
            operator_id=operator_id,
            run_id=run_id,
            request_id=request_id,
            execution_id=execution_id,
            target_endpoint=target_endpoint,
        )

    def run(self, req: FinancialSandboxRequest) -> FinancialSandboxResult:
        if self._settings.require_human_approval:
            row = self._db.fetchone(
                "SELECT status FROM exercise_runs WHERE run_id = :run_id",
                {"run_id": str(req.run_id)},
            )
            if not row or row.get("status") != "approved":
                raise ApprovalRequiredError("Financial simulation requires approved run", run_id=str(req.run_id))

        self._scope.assert_operator(req.operator_id, request_id=req.request_id)
        start = time.perf_counter()
        simulation_id = uuid4()
        emulation_result = None

        if req.target_context and req.execution_payload:
            emulation_result = self._adversary.execute(
                target=req.target_context,
                payload=req.execution_payload,
                operator_id=req.operator_id,
                run_id=req.run_id,
                request_id=req.request_id,
            )

        payload_id = req.payload_id or _TECHNIQUE_PAYLOADS.get(req.technique, "")
        payload_results: list[dict] = []
        mock_transactions: list[dict] = []

        variables = {
            **req.variables,
            "merchant_id": req.mock_merchant_id,
            "run_id": str(req.run_id),
            "scenario_id": req.scenario_id,
            "technique": req.technique,
        }

        if payload_id:
            try:
                payload_results.append(
                    self._payloads.execute(
                        payload_id=payload_id,
                        arena_target_id=self._resolve_financial_target_id(),
                        variables=variables,
                        operator_id=req.operator_id,
                    )
                )
            except Exception as exc:
                logger.warning("Payload execution failed, using direct mock API: %s", exc)

        stripe_url = self._settings.resolve_financial_stripe_url()
        iban_url = self._settings.resolve_financial_iban_url()
        self._scope.assert_url_in_scope(stripe_url, request_id=req.request_id)
        self._scope.assert_url_in_scope(iban_url, request_id=req.request_id)
        audit = AuditHttpContext(
            request_id=req.request_id,
            operator_id=req.operator_id,
            run_id=req.run_id,
            tool="financial_sandbox",
            action=req.technique,
        )

        if req.technique in {"payment_api_abuse", "invoice_substitution", "beneficiary_swap"}:
            tx = self._http.post_json(
                f"{stripe_url}/v1/payment_intents",
                {
                    "merchant_id": req.mock_merchant_id,
                    "amount_eur": float(req.variables.get("amount_eur", 12500.0)),
                    "metadata": {"synthetic": True, "technique": req.technique, "run_id": str(req.run_id)},
                },
                audit=audit,
            )
            mock_transactions.append(tx)

        if req.technique in {"invoice_substitution", "beneficiary_swap"}:
            iban_resp = self._http.post_json(
                f"{iban_url}/v1/validate",
                {
                    "iban": str(req.variables.get("iban_to", "DE00000000000000000000")),
                    "merchant_id": req.mock_merchant_id,
                },
                audit=audit,
            )
            mock_transactions.append(iban_resp)

        substitution_detected = self._detect_substitution(req.technique, mock_transactions)
        synthetic_amount = float(req.variables.get("amount_eur", 12500.0))

        ledger_path = self._ledger_dir / f"{simulation_id}.json"
        ledger_path.write_text(json.dumps(mock_transactions, indent=2) + "\n", encoding="utf-8")

        atlas = self._atlas.map_artifact(
            ATLASMapRequest(
                request_id=req.request_id,
                artifact_type="financial_impact",
                artifact={"technique": req.technique, "transactions": mock_transactions},
            )
        )

        self._db.execute(
            """
            INSERT INTO financial_simulations (
                simulation_id, run_id, operator_id, technique, mock_merchant_id,
                synthetic_amount_eur, substitution_success, guardrail_active,
                atlas_technique_ids, ledger_snapshot_path
            ) VALUES (
                :simulation_id, :run_id, :operator_id, :technique, :mock_merchant_id,
                :synthetic_amount_eur, :substitution_success, false,
                :atlas_technique_ids, :ledger_snapshot_path
            )
            """,
            {
                "simulation_id": str(simulation_id),
                "run_id": str(req.run_id),
                "operator_id": req.operator_id,
                "technique": req.technique,
                "mock_merchant_id": req.mock_merchant_id,
                "synthetic_amount_eur": synthetic_amount,
                "substitution_success": not substitution_detected,
                "atlas_technique_ids": [t.atlas_id for t in atlas.techniques],
                "ledger_snapshot_path": str(ledger_path),
            },
        )

        for tx in mock_transactions:
            self._db.execute(
                """
                INSERT INTO synthetic_ledger (entry_id, simulation_id, merchant_id, iban_from, iban_to, amount_eur, status, synthetic)
                VALUES (:entry_id, :simulation_id, :merchant_id, :iban_from, :iban_to, :amount_eur, :status, true)
                """,
                {
                    "entry_id": str(uuid4()),
                    "simulation_id": str(simulation_id),
                    "merchant_id": req.mock_merchant_id,
                    "iban_from": str(req.variables.get("iban_from", "DE00000000000000000001")),
                    "iban_to": str(req.variables.get("iban_to", "DE00000000000000000000")),
                    "amount_eur": synthetic_amount,
                    "status": "completed" if not substitution_detected else "blocked",
                },
            )

        duration_ms = int((time.perf_counter() - start) * 1000)
        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=req.request_id,
                tool="financial_sandbox",
                operator_id=req.operator_id,
                action="run",
                outcome="pass",
                payload_hash=sha256_payload(req.model_dump(mode="json")),
                duration_ms=duration_ms,
                run_id=req.run_id,
            )

        return FinancialSandboxResult(
            request_id=req.request_id,
            simulation_id=simulation_id,
            technique=req.technique,
            mock_transactions=mock_transactions,
            synthetic_amount_eur=synthetic_amount,
            substitution_detected=substitution_detected,
            ledger_snapshot_path=str(ledger_path),
            atlas_technique_ids=[t.atlas_id for t in atlas.techniques],
            payload_results=payload_results,
            emulation_result=emulation_result,
            completed_at=datetime.now(tz=timezone.utc),
        )

    def _resolve_financial_target_id(self) -> str:
        for target_id, target in self._scope.scope.targets.items():
            if "financial" in target.allowed_techniques or "payment" in target.metadata.get("type", ""):
                return target_id
        if self._scope.scope.targets:
            return next(iter(self._scope.scope.targets))
        return "arena-default"

    @staticmethod
    def _detect_substitution(technique: str, transactions: list[dict]) -> bool:
        if technique not in {"invoice_substitution", "beneficiary_swap"}:
            return False
        for tx in transactions:
            if tx.get("blocked") is True or tx.get("status") == "blocked":
                return True
            if tx.get("valid") is False:
                return True
        return False
