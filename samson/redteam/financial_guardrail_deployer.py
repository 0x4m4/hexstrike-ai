"""Production runtime deployer for financial guardrail proxy middleware (ADR-004/005)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ConfigurationError
from samson.redteam.guardrail.config_compiler import GuardrailConfigCompiler
from samson.redteam.guardrail.proxy_middleware import AsyncFinancialGuardrailProxy
from samson.redteam.schemas import (
    AdversaryEmulationResult,
    FinancialGuardrailDeployRequest,
    FinancialGuardrailDeployResult,
    GuardrailEnforcementConfig,
    ProxyMiddlewareConfig,
)

logger = logging.getLogger(__name__)


class FinancialGuardrailDeployer:
    """
    Loads AdversaryEmulationResult from PostgreSQL, compiles local proxy middleware
    configuration, and starts async outbound inspection with IBAN whitelist enforcement.
    """

    def __init__(self, settings: SamsonSettings | None = None, *, database_url: str | None = None) -> None:
        if database_url:
            settings = SamsonSettings(database_url=database_url)
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._compiler = GuardrailConfigCompiler(self._settings)
        self._proxy = AsyncFinancialGuardrailProxy(self._settings)
        self._active_deployment_id: UUID | None = None

    @property
    def proxy(self) -> AsyncFinancialGuardrailProxy:
        return self._proxy

    async def close(self) -> None:
        """Release bound proxy sockets so the next audit round can rebind :8787."""
        try:
            await self._proxy.stop()
        finally:
            self._active_deployment_id = None

    async def close_proxy(self) -> None:
        """Alias for :meth:`close` — guaranteed teardown entrypoint for Round-2 finally blocks."""
        await self.close()

    async def deploy_from_execution(self, req: FinancialGuardrailDeployRequest) -> FinancialGuardrailDeployResult:
        start = datetime.now(timezone.utc)
        row = await asyncio.to_thread(self._load_execution_row, req.execution_id)
        if not row:
            raise ConfigurationError(
                f"Adversary emulation result not found: {req.execution_id}",
                execution_id=str(req.execution_id),
            )

        emulation = self._row_to_emulation(row)
        upstream = req.upstream_base_url or self._settings.arena_base_url_str

        proxy_config, enforcement = self._compiler.compile_from_emulation(
            emulation=emulation,
            execution_id=req.execution_id,
            operator_id=req.operator_id,
            run_id=req.run_id or (UUID(str(row["run_id"])) if row.get("run_id") else None),
            upstream_base_url=upstream,
            policy_profile=req.policy_profile,
        )

        if self._proxy.is_running:
            await self._proxy.stop()

        await self._proxy.start(proxy_config)
        self._active_deployment_id = proxy_config.deployment_id

        await asyncio.to_thread(self._persist_deployment, proxy_config, enforcement, emulation, req)

        if self._settings.audit_enabled:
            await asyncio.to_thread(
                self._audit.write_redteam_audit,
                request_id=req.request_id,
                tool="financial_guardrail_deployer",
                operator_id=req.operator_id,
                action="deploy",
                outcome="pass",
                payload_hash=sha256_payload(req.model_dump(mode="json")),
                duration_ms=int((datetime.now(timezone.utc) - start).total_seconds() * 1000),
                run_id=req.run_id,
            )

        return FinancialGuardrailDeployResult(
            request_id=req.request_id,
            deployment_id=proxy_config.deployment_id,
            execution_id=req.execution_id,
            proxy_config=proxy_config,
            guardrail_config=enforcement,
            listen_url=f"http://{proxy_config.listen_host}:{proxy_config.listen_port}",
            blocked_ibans=proxy_config.blocked_ibans,
            status="active",
            completed_at=datetime.now(timezone.utc),
        )

    async def teardown(self, deployment_id: UUID, operator_id: str, request_id: UUID) -> None:
        await self._proxy.stop()
        await asyncio.to_thread(
            self._db.execute,
            """
            UPDATE guardrail_proxy_deployments
            SET status = 'destroyed', destroyed_at = NOW()
            WHERE deployment_id = :deployment_id
            """,
            {"deployment_id": str(deployment_id)},
        )
        if self._settings.audit_enabled:
            await asyncio.to_thread(
                self._audit.write_redteam_audit,
                request_id=request_id,
                tool="financial_guardrail_deployer",
                operator_id=operator_id,
                action="teardown",
                outcome="pass",
                payload_hash=sha256_payload({"deployment_id": str(deployment_id)}),
                duration_ms=0,
                run_id=None,
            )
        self._active_deployment_id = None

    async def inspect_outbound(self, text: str, *, request_path: str = "/inspect"):
        """Programmatic inspection without forwarding — used by tests and orchestrator validation."""
        return await self._proxy.inspect_text(text, request_path=request_path)

    def _load_execution_row(self, execution_id: UUID) -> dict[str, Any] | None:
        return self._db.fetchone(
            """
            SELECT execution_id, target_id, payload_id, run_id, operator_id,
                   attack_vector, interface_type, http_status_code, vulnerability_verified,
                   response_payload, intercepted_financial_entities
            FROM adversary_emulation_results
            WHERE execution_id = :execution_id
            """,
            {"execution_id": str(execution_id)},
        )

    @staticmethod
    def _row_to_emulation(row: dict[str, Any]) -> AdversaryEmulationResult:
        payload = row.get("response_payload")
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            payload = {}
        entities = row.get("intercepted_financial_entities") or []
        return AdversaryEmulationResult(
            execution_id=UUID(str(row["execution_id"])),
            vulnerability_verified=bool(row["vulnerability_verified"]),
            http_status_code=int(row["http_status_code"]),
            response_payload=payload,
            intercepted_financial_entities=[str(e) for e in entities],
        )

    def _persist_deployment(
        self,
        proxy_config: ProxyMiddlewareConfig,
        enforcement: GuardrailEnforcementConfig,
        emulation: AdversaryEmulationResult,
        req: FinancialGuardrailDeployRequest,
    ) -> None:
        self._db.execute(
            """
            INSERT INTO guardrail_proxy_deployments (
                deployment_id, execution_id, run_id, operator_id, policy_profile,
                listen_host, listen_port, upstream_base_url, config_path, proxy_config,
                enforcement_config, blocked_ibans, status
            ) VALUES (
                :deployment_id, :execution_id, :run_id, :operator_id, :policy_profile,
                :listen_host, :listen_port, :upstream_base_url, :config_path,
                CAST(:proxy_config AS jsonb), CAST(:enforcement_config AS jsonb), :blocked_ibans, 'active'
            )
            """,
            {
                "deployment_id": str(proxy_config.deployment_id),
                "execution_id": str(req.execution_id),
                "run_id": str(proxy_config.run_id) if proxy_config.run_id else None,
                "operator_id": req.operator_id,
                "policy_profile": proxy_config.policy_profile,
                "listen_host": proxy_config.listen_host,
                "listen_port": proxy_config.listen_port,
                "upstream_base_url": proxy_config.upstream_base_url,
                "config_path": proxy_config.config_path or "",
                "proxy_config": proxy_config.model_dump_json(),
                "enforcement_config": enforcement.model_dump_json(),
                "blocked_ibans": proxy_config.blocked_ibans,
            },
        )
        if proxy_config.run_id:
            self._db.execute(
                """
                UPDATE financial_guardrail_deployments
                SET status = 'destroyed', destroyed_at = NOW()
                WHERE status = 'active'
                  AND simulation_id IN (
                    SELECT simulation_id FROM financial_simulations WHERE run_id = :run_id
                  )
                """,
                {"run_id": str(proxy_config.run_id)},
            )
