"""Async reverse-proxy middleware with outbound IBAN inspection and HITL enforcement."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

import httpx
from aiohttp import web

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.redteam.guardrail.hitl_queue import GuardrailHitlQueue
from samson.redteam.guardrail.iban_validator import (
    IbanValidationStatus,
    evaluate_outbound_ibans,
    extract_ibans,
    normalize_iban,
)
from samson.redteam.schemas import GuardrailInterceptionDecision, ProxyMiddlewareConfig

logger = logging.getLogger(__name__)


class InterceptionAction(str, Enum):
    ALLOW = "allow"
    DROP = "drop"
    HITL = "hitl"


@dataclass
class _RuntimeState:
    config: ProxyMiddlewareConfig
    whitelist: frozenset[str]
    compiled_patterns: list[re.Pattern[str]]


class AsyncFinancialGuardrailProxy:
    """Local async HTTP proxy that inspects outbound payloads for IBAN policy violations."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._hitl = GuardrailHitlQueue(self._settings, self._db)
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._state: _RuntimeState | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def is_running(self) -> bool:
        return self._runner is not None

    async def start(self, config: ProxyMiddlewareConfig) -> None:
        if self.is_running:
            await self.stop()

        whitelist = frozenset(normalize_iban(i) for i in config.iban_whitelist)
        patterns = [re.compile(p, re.IGNORECASE) for p in config.strict_regex_patterns]
        self._state = _RuntimeState(config=config, whitelist=whitelist, compiled_patterns=patterns)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._settings.http_timeout_sec),
            follow_redirects=False,
            verify=True,
        )

        self._app = web.Application()
        self._app.router.add_route("*", "/{path_info:.*}", self._handle_request)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        # reuse_address=True: surrender :8787 immediately across rapid audit rounds (TIME_WAIT-safe)
        self._site = web.TCPSite(
            self._runner,
            config.listen_host,
            config.listen_port,
            shutdown_timeout=5.0,
            reuse_address=True,
            reuse_port=False,
        )
        await self._site.start()
        logger.info(
            "Financial guardrail proxy listening on %s:%s -> %s (reuse_address=True)",
            config.listen_host,
            config.listen_port,
            config.upstream_base_url,
        )

    async def stop(self) -> None:
        """Tear down TCP site, runner, and upstream client; always clears runtime state."""
        site = self._site
        runner = self._runner
        client = self._client
        self._site = None
        self._runner = None
        self._client = None
        self._state = None
        self._app = None

        if site is not None:
            try:
                await site.stop()
            except Exception as exc:  # noqa: BLE001 — cleanup must not raise into audit loops
                logger.warning("Guardrail proxy site stop failed: %s", exc)
        if runner is not None:
            try:
                await runner.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Guardrail proxy runner cleanup failed: %s", exc)
        if client is not None:
            try:
                await client.aclose()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Guardrail proxy HTTP client close failed: %s", exc)

        # Yield to the event loop so the OS can reclaim the bound port before the next start().
        await asyncio.sleep(0)

    async def inspect_text(self, text: str, *, request_path: str) -> GuardrailInterceptionDecision:
        if not self._state:
            raise RuntimeError("Guardrail proxy is not running")
        config = self._state.config
        validations = evaluate_outbound_ibans(text, self._state.whitelist)

        blocked_ibans = [
            v.normalized
            for v in validations
            if v.status
            in {IbanValidationStatus.VALID_NOT_WHITELISTED, IbanValidationStatus.INVALID_CHECKSUM}
        ]
        for pattern in self._state.compiled_patterns:
            if pattern.search(text):
                for iban in extract_ibans(text):
                    if iban not in config.iban_whitelist and iban not in blocked_ibans:
                        blocked_ibans.append(iban)

        blocked_ibans = sorted(set(blocked_ibans))
        # Body + path/query: outbound wallet destinations often appear in URL or JSON body.
        haystack = f"{text}\n{request_path}"
        blocked_web3 = self._find_blocked_web3(haystack, config.blocked_web3_addresses)
        pattern_hit = any(p.search(haystack) for p in self._state.compiled_patterns)
        if not blocked_ibans and not blocked_web3 and not pattern_hit:
            return GuardrailInterceptionDecision(
                action=InterceptionAction.ALLOW.value,
                blocked_ibans=[],
                blocked_web3_addresses=[],
                reason="No policy violations detected",
                request_path=request_path,
            )

        action = (
            InterceptionAction.HITL.value
            if config.enforce_human_approval and config.on_mismatch_action == "hitl"
            else InterceptionAction.DROP.value
        )
        reason_parts = []
        if blocked_ibans:
            reason_parts.append("IBAN policy mismatch")
        if blocked_web3:
            reason_parts.append("Arkham high-risk Web3 address")
        if pattern_hit and not reason_parts:
            reason_parts.append("pattern policy mismatch")
        return GuardrailInterceptionDecision(
            action=action,
            blocked_ibans=blocked_ibans,
            blocked_web3_addresses=blocked_web3,
            reason=f"{'; '.join(reason_parts)} on path {request_path}",
            request_path=request_path,
        )

    async def _handle_request(self, request: web.Request) -> web.StreamResponse:
        if not self._state or not self._client:
            return web.Response(status=503, text="Guardrail proxy not initialized")

        config = self._state.config
        body_bytes = await request.read()
        body_text = body_bytes.decode("utf-8", errors="replace")
        path = request.path_qs

        decision = await self.inspect_text(body_text, request_path=path)
        await self._audit_request(
            config=config,
            path=path,
            method=request.method,
            decision=decision,
            body_hash=hashlib.sha256(body_bytes).hexdigest(),
        )

        if decision.action == InterceptionAction.DROP.value:
            return web.json_response(
                {
                    "status": "blocked",
                    "reason": decision.reason,
                    "blocked_ibans": decision.blocked_ibans,
                    "blocked_web3_addresses": decision.blocked_web3_addresses,
                    "deployment_id": str(config.deployment_id),
                },
                status=403,
            )

        if decision.action == InterceptionAction.HITL.value:
            pending = await self._hitl.enqueue(
                deployment_id=config.deployment_id,
                operator_id=config.operator_id,
                run_id=config.run_id,
                intercepted_ibans=decision.blocked_ibans,
                request_body=body_text,
                request_path=path,
                reason=decision.reason,
            )
            return web.json_response(
                {
                    "status": "awaiting_operator_review",
                    "pending_id": str(pending.pending_id),
                    "blocked_ibans": decision.blocked_ibans,
                    "blocked_web3_addresses": decision.blocked_web3_addresses,
                    "deployment_id": str(config.deployment_id),
                },
                status=202,
            )

        upstream_url = f"{config.upstream_base_url.rstrip('/')}{path}"
        await self._assert_upstream_host_allowed(upstream_url)

        try:
            upstream_response = await self._client.request(
                method=request.method,
                url=upstream_url,
                content=body_bytes,
                headers=self._forward_headers(request),
            )
        except httpx.HTTPError as exc:
            logger.error("Upstream forward failed: %s", exc)
            return web.Response(status=502, text=f"Upstream error: {exc}")

        return web.Response(
            status=upstream_response.status_code,
            body=upstream_response.content,
            headers={
                k: v
                for k, v in upstream_response.headers.items()
                if k.lower() not in {"transfer-encoding", "content-encoding", "content-length"}
            },
        )

    async def _assert_upstream_host_allowed(self, url: str) -> None:
        from urllib.parse import urlparse

        if not self._state:
            return
        host = urlparse(url).hostname or ""
        if host not in self._state.config.allowed_destination_hosts:
            raise web.HTTPForbidden(text=f"Destination host not allowlisted: {host}")

    @staticmethod
    def _find_blocked_web3(text: str, blocked: list[str]) -> list[str]:
        if not blocked or not text:
            return []
        lowered = text.lower()
        hits: list[str] = []
        for addr in blocked:
            needle = addr.lower()
            if needle in lowered:
                hits.append(needle)
        return sorted(set(hits))

    @staticmethod
    def _forward_headers(request: web.Request) -> dict[str, str]:
        skip = {"host", "content-length", "transfer-encoding"}
        return {k: v for k, v in request.headers.items() if k.lower() not in skip}

    async def _audit_request(
        self,
        *,
        config: ProxyMiddlewareConfig,
        path: str,
        method: str,
        decision: GuardrailInterceptionDecision,
        body_hash: str,
    ) -> None:
        if not self._settings.audit_enabled:
            return
        payload = {
            "method": method,
            "path": path,
            "action": decision.action,
            "blocked_ibans": decision.blocked_ibans,
            "blocked_web3_addresses": decision.blocked_web3_addresses,
            "body_hash": body_hash,
        }

        def _write() -> None:
            self._audit.write_redteam_audit(
                request_id=config.deployment_id,
                tool="financial_guardrail_proxy",
                operator_id=config.operator_id,
                action=f"intercept_{decision.action}",
                outcome="pass" if decision.action == InterceptionAction.ALLOW.value else "hold",
                payload_hash=sha256_payload(payload),
                duration_ms=0,
                run_id=config.run_id,
            )

        await asyncio.to_thread(_write)
