"""Multi-source hybrid reconnaissance — FOFA + unified ShodanReconArtifact schema.

Production async client for authorized Redis (port 6379) exposure hunting via
official FOFA API:

    GET https://fofa.info/api/v1/search/all?key={api_key}&qbase64={base64_query}

Hard rules:
- API keys from env only (``SAMSON_FOFA_API_KEY`` / ``FOFA_API_KEY``)
- Postgres cache short-circuit before any live FOFA call (0 credits)
- Strict 5-second rate limiter (process-local + shared budget row)
- Normalize FOFA matrix rows into ``ShodanReconArtifact`` for unified persistence
"""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID, uuid4

import httpx

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ConfigurationError, NetworkError
from samson.core.scope import ScopeEnforcer
from samson.core.target_loader import IngestedTargetKind, TargetLoader
from samson.redteam.schemas import (
    ApiCreditBudget,
    FofaCollectResult,
    HybridReconResult,
    ShodanReconArtifact,
    ShodanServiceBanner,
)

logger = logging.getLogger(__name__)

_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)
_REDIS_PORT = 6379
_DEFAULT_FIELDS = (
    "ip,port,protocol,country,city,host,title,banner,server,os,asn,org,header"
)
_REDIS_GLOBAL_QUERY = 'port="6379" && protocol="redis"'

SELECT_BUDGET_QUERY = """
SELECT budget_id, provider, credits_remaining, credits_total,
       min_interval_sec, last_query_at, is_blocked, updated_at
FROM api_credit_budgets
WHERE budget_id = :budget_id
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def encode_fofa_query(query: str) -> str:
    """UTF-8 → Base64 for FOFA ``qbase64`` parameter."""
    return base64.b64encode(query.encode("utf-8")).decode("ascii")


def build_redis_host_query(ip_address: str) -> str:
    """Authorized per-host Redis exposure query."""
    ip = str(ipaddress.ip_address(ip_address.strip()))
    return f'ip="{ip}" && port="6379"'


class SamsonFofaClient:
    """Async FOFA client: cache-first → budget → 5s rate-limit → live search."""

    def __init__(
        self,
        settings: SamsonSettings | None = None,
        *,
        api_key: str | None = None,
        api_email: str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._api_key = (api_key or self._settings.fofa_api_key or "").strip()
        self._api_email = (api_email or self._settings.fofa_api_email or "").strip()
        self._base_url = str(self._settings.fofa_api_base_url).rstrip("/")
        self._budget_id = self._settings.fofa_budget_id
        self._reserve = int(self._settings.fofa_reserve_credits)
        self._min_interval = float(self._settings.fofa_min_interval_sec)
        self._cache_ttl = int(self._settings.fofa_cache_ttl_sec)
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._scope = ScopeEnforcer(self._settings)
        self._client: httpx.AsyncClient | None = None
        self._rate_lock = asyncio.Lock()
        self._last_query_monotonic: float | None = None

    async def __aenter__(self) -> SamsonFofaClient:
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_account_info(self) -> dict[str, Any]:
        """GET /api/v1/info/my — sync local FOFA credit budget from account."""
        if not self._api_key:
            raise ConfigurationError(
                "FOFA API key missing — set SAMSON_FOFA_API_KEY or FOFA_API_KEY"
            )
        client = await self._ensure_client()
        params = self._auth_params()
        httpx_log = logging.getLogger("httpx")
        prev = httpx_log.level
        try:
            httpx_log.setLevel(logging.WARNING)
            response = await client.get(f"{self._base_url}/api/v1/info/my", params=params)
        except httpx.HTTPError as exc:
            raise NetworkError("FOFA account info transport failure", error=str(exc)) from exc
        finally:
            httpx_log.setLevel(prev)

        if response.status_code >= 400:
            raise NetworkError(
                f"FOFA account info failed HTTP {response.status_code}",
                status_code=response.status_code,
                body=response.text[:1000],
            )
        payload = response.json()
        if payload.get("error") is True:
            raise ConfigurationError(
                f"FOFA account info error: {payload.get('errmsg') or payload}",
            )
        await asyncio.to_thread(self._sync_budget_from_account, payload)
        return payload if isinstance(payload, dict) else {}

    async def hunt_redis_for_ip(
        self,
        ip_address: str,
        *,
        operator_id: str = "operator-alpha",
        request_id: UUID | None = None,
        run_id: UUID | None = None,
        force_refresh: bool = False,
        size: int | None = None,
    ) -> FofaCollectResult:
        """Cache-first Redis (6379) hunt for a single authorized host IP."""
        request_id = request_id or uuid4()
        ip = str(ipaddress.ip_address((ip_address or "").strip()))
        self._scope.assert_operator(operator_id, request_id=request_id)
        query = build_redis_host_query(ip)

        if not force_refresh:
            cached = await asyncio.to_thread(self.get_cached_recon, ip)
            if cached is not None:
                budget = await asyncio.to_thread(self._load_or_init_budget)
                logger.info(
                    "[+] FOFA cache hit for %s — 0 credits spent; remaining=%s",
                    ip,
                    budget.credits_remaining,
                )
                if self._settings.audit_enabled:
                    await asyncio.to_thread(
                        self._audit.write_redteam_audit,
                        request_id=request_id,
                        tool="fofa_hybrid_recon",
                        operator_id=operator_id,
                        action="hunt_redis_cache_hit",
                        outcome="pass",
                        payload_hash=sha256_payload(
                            {"ip": ip, "artifact_id": str(cached.artifact_id)}
                        ),
                        duration_ms=0,
                        run_id=run_id,
                    )
                artifact = cached.model_copy(
                    update={"request_id": request_id, "operator_id": operator_id}
                )
                return FofaCollectResult(
                    request_id=request_id,
                    query=query,
                    ip_address=ip,
                    from_cache=True,
                    credits_spent=0,
                    credits_remaining=budget.credits_remaining,
                    result_count=1,
                    artifacts=[artifact],
                    artifact=artifact,
                    http_status_code=200,
                )

        return await self.search(
            query,
            operator_id=operator_id,
            request_id=request_id,
            run_id=run_id,
            size=size,
            primary_ip=ip,
        )

    async def search(
        self,
        query: str,
        *,
        operator_id: str = "operator-alpha",
        request_id: UUID | None = None,
        run_id: UUID | None = None,
        size: int | None = None,
        fields: str = _DEFAULT_FIELDS,
        primary_ip: str | None = None,
    ) -> FofaCollectResult:
        """Execute a live FOFA search with budget + rate-limit enforcement."""
        request_id = request_id or uuid4()
        q = (query or "").strip()
        if not q:
            raise ConfigurationError("FOFA query must not be empty")
        self._scope.assert_operator(operator_id, request_id=request_id)

        if not self._api_key:
            raise ConfigurationError(
                "FOFA API key missing — set SAMSON_FOFA_API_KEY or FOFA_API_KEY",
                budget_id=self._budget_id,
            )

        budget = await asyncio.to_thread(self._load_or_init_budget)
        if budget.credits_remaining <= self._reserve or budget.is_blocked:
            await self._block_and_audit(
                request_id=request_id,
                operator_id=operator_id,
                run_id=run_id,
                query=q,
                budget=budget,
                reason=(
                    f"FOFA credit floor reached "
                    f"(remaining={budget.credits_remaining} <= reserve={self._reserve})"
                ),
            )
            return FofaCollectResult(
                request_id=request_id,
                query=q,
                ip_address=primary_ip,
                is_blocked=True,
                block_reason="credits_reserve_reached",
                credits_remaining=budget.credits_remaining,
            )

        await self._enforce_rate_limit(self._min_interval)
        budget = await asyncio.to_thread(self._load_or_init_budget)
        if budget.credits_remaining <= self._reserve or budget.is_blocked:
            return FofaCollectResult(
                request_id=request_id,
                query=q,
                ip_address=primary_ip,
                is_blocked=True,
                block_reason="credits_reserve_reached",
                credits_remaining=budget.credits_remaining,
            )

        client = await self._ensure_client()
        page_size = int(size if size is not None else self._settings.fofa_default_size)
        page_size = max(1, min(page_size, 10_000))
        params = {
            **self._auth_params(),
            "qbase64": encode_fofa_query(q),
            "size": str(page_size),
            "fields": fields,
        }

        started = time.perf_counter()
        httpx_log = logging.getLogger("httpx")
        prev = httpx_log.level
        try:
            httpx_log.setLevel(logging.WARNING)
            logger.info(
                "FOFA GET %s/api/v1/search/all q=%r (api_key=REDACTED)",
                self._base_url,
                q,
            )
            response = await client.get(
                f"{self._base_url}/api/v1/search/all",
                params=params,
            )
        except httpx.HTTPError as exc:
            raise NetworkError(
                "FOFA search transport failure",
                query=q,
                error=str(exc),
            ) from exc
        finally:
            httpx_log.setLevel(prev)

        duration_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code == 401:
            raise ConfigurationError("FOFA API key rejected (401)")
        if response.status_code == 429:
            await self._block_and_audit(
                request_id=request_id,
                operator_id=operator_id,
                run_id=run_id,
                query=q,
                budget=budget,
                reason="FOFA HTTP 429 rate limit",
            )
            return FofaCollectResult(
                request_id=request_id,
                query=q,
                ip_address=primary_ip,
                is_blocked=True,
                block_reason="http_429",
                credits_remaining=budget.credits_remaining,
                http_status_code=429,
                errmsg="rate limited",
            )
        if response.status_code >= 400:
            raise NetworkError(
                f"FOFA search failed HTTP {response.status_code}",
                status_code=response.status_code,
                body=response.text[:2000],
            )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise NetworkError("FOFA returned non-JSON payload", query=q) from exc

        if not isinstance(payload, dict):
            raise NetworkError("FOFA payload must be a JSON object", query=q)

        if payload.get("error") is True:
            errmsg = str(payload.get("errmsg") or "unknown FOFA error")
            # Insufficient F-points / API quota — mark budget blocked, do not crash bulk loop.
            lowered = errmsg.lower()
            if any(
                token in lowered
                for token in ("余额不足", "f点", "820031", "点数不足", "remain_api")
            ) or "不足" in errmsg:
                new_budget = await asyncio.to_thread(self._mark_budget_exhausted)
                await self._block_and_audit(
                    request_id=request_id,
                    operator_id=operator_id,
                    run_id=run_id,
                    query=q,
                    budget=new_budget,
                    reason=f"FOFA API error: {errmsg}",
                )
                return FofaCollectResult(
                    request_id=request_id,
                    query=q,
                    ip_address=primary_ip,
                    is_blocked=True,
                    block_reason="fofa_quota_exhausted",
                    credits_spent=0,
                    credits_remaining=new_budget.credits_remaining,
                    http_status_code=response.status_code,
                    errmsg=errmsg,
                )
            raise NetworkError("FOFA search API error", query=q, errmsg=errmsg)

        field_names = self._resolve_fields(payload.get("fields"), fields)
        rows = payload.get("results") or []
        if not isinstance(rows, list):
            rows = []

        artifacts = self._normalize_results(
            rows,
            field_names=field_names,
            request_id=request_id,
            operator_id=operator_id,
            query=q,
            raw_envelope=payload,
        )
        for artifact in artifacts:
            await asyncio.to_thread(self._persist_artifact, artifact, run_id=run_id, query=q)

        new_budget = await asyncio.to_thread(self._consume_credit, budget)
        if self._settings.audit_enabled:
            await asyncio.to_thread(
                self._audit.write_redteam_audit,
                request_id=request_id,
                tool="fofa_hybrid_recon",
                operator_id=operator_id,
                action="search",
                outcome="pass",
                payload_hash=sha256_payload(
                    {
                        "query": q,
                        "result_count": len(rows),
                        "artifact_count": len(artifacts),
                    }
                ),
                duration_ms=duration_ms,
                run_id=run_id,
            )

        primary = None
        if primary_ip:
            primary = next(
                (a for a in artifacts if a.ip_address == primary_ip),
                artifacts[0] if artifacts else None,
            )
        elif artifacts:
            primary = artifacts[0]

        logger.warning(
            "FOFA search q=%r hits=%d artifacts=%d credits_remaining=%s",
            q,
            len(rows),
            len(artifacts),
            new_budget.credits_remaining,
        )
        return FofaCollectResult(
            request_id=request_id,
            query=q,
            ip_address=primary_ip or (primary.ip_address if primary else None),
            from_cache=False,
            credits_spent=1,
            credits_remaining=new_budget.credits_remaining,
            result_count=len(rows),
            artifacts=artifacts,
            artifact=primary,
            http_status_code=response.status_code,
        )

    def get_cached_recon(self, target_ip: str) -> ShodanReconArtifact | None:
        """Return newest FOFA artifact for IP within TTL, or None."""
        row = self._db.fetchone(
            """
            SELECT artifact_id, request_id, operator_id, ip_address, hostnames,
                   org, isp, asn, os, country_code, city, open_ports, banners,
                   detected_vulnerabilities, raw_payload, rag_doc_path, collected_at
            FROM fofa_recon_artifacts
            WHERE ip_address = :ip
              AND collected_at >= NOW() - (:ttl * INTERVAL '1 second')
            ORDER BY collected_at DESC
            LIMIT 1
            """,
            {"ip": target_ip.strip(), "ttl": self._cache_ttl},
        )
        if not row:
            return None
        return self._row_to_artifact(row)

    def _auth_params(self) -> dict[str, str]:
        params = {"key": self._api_key}
        if self._api_email:
            params["email"] = self._api_email
        return params

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._settings.http_timeout_sec),
                headers={
                    "Accept": "application/json",
                    "User-Agent": self._settings.http_user_agent,
                },
                follow_redirects=True,
            )
        return self._client

    async def _enforce_rate_limit(self, min_interval_sec: float) -> None:
        """Strict 5-second FOFA limiter (local lock + shared Postgres last_query_at)."""
        interval = max(float(min_interval_sec), 5.0)
        async with self._rate_lock:
            now = time.monotonic()
            if self._last_query_monotonic is not None:
                remaining = interval - (now - self._last_query_monotonic)
                if remaining > 0:
                    logger.info("FOFA rate-limit sleep %.2fs (local)", remaining)
                    await asyncio.sleep(remaining)

            while True:
                wait_sec = await asyncio.to_thread(self._db_rate_wait_seconds, interval)
                if wait_sec <= 0:
                    break
                logger.info("FOFA rate-limit sleep %.2fs (postgres)", wait_sec)
                await asyncio.sleep(wait_sec)

            self._last_query_monotonic = time.monotonic()

    def _db_rate_wait_seconds(self, interval: float) -> float:
        row = self._db.fetchone(
            """
            SELECT EXTRACT(EPOCH FROM (NOW() - last_query_at)) AS elapsed
            FROM api_credit_budgets
            WHERE budget_id = :budget_id AND last_query_at IS NOT NULL
            """,
            {"budget_id": self._budget_id},
        )
        if not row or row.get("elapsed") is None:
            return 0.0
        remaining = float(interval) - float(row["elapsed"])
        return remaining if remaining > 0 else 0.0

    def _load_or_init_budget(self) -> ApiCreditBudget:
        row = self._db.fetchone(SELECT_BUDGET_QUERY, {"budget_id": self._budget_id})
        if not row:
            self._db.execute(
                """
                INSERT INTO api_credit_budgets (
                    budget_id, provider, credits_remaining, credits_total,
                    min_interval_sec, is_blocked
                ) VALUES (
                    :budget_id, 'fofa', :credits, :credits, :min_interval, FALSE
                )
                """,
                {
                    "budget_id": self._budget_id,
                    "credits": int(self._settings.fofa_initial_credits),
                    "min_interval": float(self._min_interval),
                },
            )
            return ApiCreditBudget(
                budget_id=self._budget_id,
                provider="fofa",
                credits_remaining=int(self._settings.fofa_initial_credits),
                credits_total=int(self._settings.fofa_initial_credits),
                min_interval_sec=float(self._min_interval),
                is_blocked=False,
            )
        return self._budget_from_row(row)

    def _sync_budget_from_account(self, payload: dict[str, Any]) -> None:
        remain_api = payload.get("remain_api_query")
        fcoin = payload.get("fofa_point", payload.get("fcoin"))
        try:
            remaining = int(remain_api) if remain_api is not None else int(fcoin or 0)
        except (TypeError, ValueError):
            remaining = 0
        remaining = max(0, remaining)
        blocked = remaining <= self._reserve
        self._db.execute(
            """
            INSERT INTO api_credit_budgets (
                budget_id, provider, credits_remaining, credits_total,
                min_interval_sec, is_blocked, updated_at
            ) VALUES (
                :budget_id, 'fofa', :remaining, :remaining, :min_interval, :blocked, NOW()
            )
            ON CONFLICT (budget_id) DO UPDATE SET
                credits_remaining = EXCLUDED.credits_remaining,
                credits_total = GREATEST(api_credit_budgets.credits_total, EXCLUDED.credits_total),
                is_blocked = EXCLUDED.is_blocked,
                min_interval_sec = EXCLUDED.min_interval_sec,
                updated_at = NOW()
            """,
            {
                "budget_id": self._budget_id,
                "remaining": remaining,
                "min_interval": float(self._min_interval),
                "blocked": blocked,
            },
        )
        logger.info(
            "FOFA budget synced remain_api_query=%s blocked=%s",
            remaining,
            blocked,
        )

    def _consume_credit(self, budget: ApiCreditBudget) -> ApiCreditBudget:
        row = self._db.fetchone(
            """
            UPDATE api_credit_budgets
            SET credits_remaining = GREATEST(credits_remaining - 1, 0),
                last_query_at = NOW(),
                is_blocked = CASE
                    WHEN GREATEST(credits_remaining - 1, 0) <= :reserve THEN TRUE
                    ELSE FALSE
                END,
                updated_at = NOW()
            WHERE budget_id = :budget_id
            RETURNING credits_remaining, is_blocked, last_query_at, updated_at,
                      credits_total, min_interval_sec, provider
            """,
            {"budget_id": budget.budget_id, "reserve": int(self._reserve)},
        )
        if not row:
            return self._load_or_init_budget()
        return self._budget_from_row(row)

    def _mark_budget_exhausted(self) -> ApiCreditBudget:
        self._db.execute(
            """
            UPDATE api_credit_budgets
            SET credits_remaining = 0,
                is_blocked = TRUE,
                last_query_at = NOW(),
                updated_at = NOW()
            WHERE budget_id = :budget_id
            """,
            {"budget_id": self._budget_id},
        )
        return self._load_or_init_budget()

    @staticmethod
    def _budget_from_row(row: dict[str, Any]) -> ApiCreditBudget:
        last_query = row.get("last_query_at")
        if isinstance(last_query, str):
            last_query = datetime.fromisoformat(last_query)
        updated = row.get("updated_at")
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)
        if updated is None:
            updated = _utcnow()
        return ApiCreditBudget(
            budget_id=str(row["budget_id"]),
            provider=str(row.get("provider") or "fofa"),
            credits_remaining=int(row["credits_remaining"]),
            credits_total=int(row.get("credits_total") or 0),
            min_interval_sec=float(row.get("min_interval_sec") or 5.0),
            last_query_at=last_query,
            is_blocked=bool(row.get("is_blocked")),
            updated_at=updated,
        )

    async def _block_and_audit(
        self,
        *,
        request_id: UUID,
        operator_id: str,
        run_id: UUID | None,
        query: str,
        budget: ApiCreditBudget,
        reason: str,
    ) -> None:
        logger.critical(
            "FOFA BLOCK: %s budget_id=%s credits_remaining=%s",
            reason,
            budget.budget_id,
            budget.credits_remaining,
        )
        await asyncio.to_thread(
            self._db.execute,
            """
            UPDATE api_credit_budgets
            SET is_blocked = TRUE, updated_at = NOW()
            WHERE budget_id = :budget_id
            """,
            {"budget_id": budget.budget_id},
        )
        if self._settings.audit_enabled:
            await asyncio.to_thread(
                self._audit.write_redteam_audit,
                request_id=request_id,
                tool="fofa_hybrid_recon",
                operator_id=operator_id,
                action="search_blocked",
                outcome="critical",
                payload_hash=sha256_payload(
                    {
                        "query": query,
                        "reason": reason,
                        "credits_remaining": budget.credits_remaining,
                    }
                ),
                duration_ms=0,
                run_id=run_id,
            )

    @staticmethod
    def _resolve_fields(payload_fields: Any, requested: str) -> list[str]:
        if isinstance(payload_fields, list) and payload_fields:
            return [str(f) for f in payload_fields]
        if isinstance(payload_fields, str) and payload_fields.strip():
            return [p.strip() for p in payload_fields.split(",") if p.strip()]
        return [p.strip() for p in requested.split(",") if p.strip()]

    def _normalize_results(
        self,
        rows: list[Any],
        *,
        field_names: list[str],
        request_id: UUID,
        operator_id: str,
        query: str,
        raw_envelope: dict[str, Any],
    ) -> list[ShodanReconArtifact]:
        by_ip: dict[str, dict[str, Any]] = {}
        for row in rows:
            mapped = self._row_to_field_map(row, field_names)
            ip = str(mapped.get("ip") or "").strip()
            if not ip:
                continue
            try:
                ip = str(ipaddress.ip_address(ip))
            except ValueError:
                continue
            bucket = by_ip.setdefault(
                ip,
                {
                    "ports": set(),
                    "banners": [],
                    "hostnames": set(),
                    "vulns": set(),
                    "org": None,
                    "asn": None,
                    "os": None,
                    "country": None,
                    "city": None,
                    "rows": [],
                },
            )
            port = self._coerce_port(mapped.get("port"))
            if port is not None:
                bucket["ports"].add(port)
            host = str(mapped.get("host") or "").strip()
            if host and host != ip:
                bucket["hostnames"].add(host)
            for key in ("org", "asn", "os", "country", "city"):
                value = mapped.get(key)
                if value and not bucket[key if key != "country" else "country"]:
                    bucket["country" if key == "country" else key] = str(value)
            banner_text = self._compose_banner(mapped)
            product = None
            protocol = str(mapped.get("protocol") or "").lower()
            server = str(mapped.get("server") or "")
            if protocol == "redis" or port == _REDIS_PORT or "redis" in server.lower():
                product = "redis"
            if banner_text or port is not None:
                bucket["banners"].append(
                    ShodanServiceBanner(
                        port=port or _REDIS_PORT,
                        transport="tcp",
                        product=product,
                        version=None,
                        banner=banner_text[:8000],
                    )
                )
            for match in _CVE_RE.findall(banner_text):
                bucket["vulns"].add(match.upper())
            if product == "redis":
                # Defensive flag for unauthenticated Redis surface (not a CVE id).
                bucket["vulns"].add("EXPOSED_REDIS_6379")
            bucket["rows"].append(mapped)

        artifacts: list[ShodanReconArtifact] = []
        for ip, bucket in by_ip.items():
            artifacts.append(
                ShodanReconArtifact(
                    artifact_id=uuid4(),
                    request_id=request_id,
                    ip_address=ip,
                    operator_id=operator_id,
                    hostnames=sorted(bucket["hostnames"]),
                    org=bucket["org"],
                    isp=None,
                    asn=bucket["asn"],
                    os=bucket["os"],
                    country_code=bucket["country"],
                    city=bucket["city"],
                    open_ports=sorted(int(p) for p in bucket["ports"]),
                    banners=list(bucket["banners"]),
                    detected_vulnerabilities=sorted(bucket["vulns"]),
                    raw_payload={
                        "source": "fofa",
                        "query": query,
                        "rows": bucket["rows"],
                        "envelope_size": raw_envelope.get("size"),
                        "envelope_page": raw_envelope.get("page"),
                        "envelope_mode": raw_envelope.get("mode"),
                    },
                    collected_at=_utcnow(),
                )
            )
        return artifacts

    @staticmethod
    def _row_to_field_map(row: Any, field_names: list[str]) -> dict[str, Any]:
        if isinstance(row, dict):
            return {str(k): v for k, v in row.items()}
        if isinstance(row, (list, tuple)):
            mapped: dict[str, Any] = {}
            for idx, name in enumerate(field_names):
                if idx < len(row):
                    mapped[name] = row[idx]
            return mapped
        return {}

    @staticmethod
    def _coerce_port(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            port = int(value)
        except (TypeError, ValueError):
            return None
        if 1 <= port <= 65535:
            return port
        return None

    @staticmethod
    def _compose_banner(mapped: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("banner", "header", "title", "server", "protocol"):
            value = mapped.get(key)
            if value:
                parts.append(str(value))
        return "\n".join(parts).strip()

    @staticmethod
    def _row_to_artifact(row: dict[str, Any]) -> ShodanReconArtifact:
        banners_raw = row.get("banners") or []
        if isinstance(banners_raw, str):
            banners_raw = json.loads(banners_raw)
        banners = [
            ShodanServiceBanner.model_validate(item)
            for item in banners_raw
            if isinstance(item, dict)
        ]
        raw_payload = row.get("raw_payload") or {}
        if isinstance(raw_payload, str):
            try:
                raw_payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                raw_payload = {}
        return ShodanReconArtifact(
            artifact_id=row["artifact_id"],
            request_id=row["request_id"],
            ip_address=row["ip_address"],
            operator_id=row["operator_id"],
            hostnames=list(row.get("hostnames") or []),
            org=row.get("org"),
            isp=row.get("isp"),
            asn=row.get("asn"),
            os=row.get("os"),
            country_code=row.get("country_code"),
            city=row.get("city"),
            open_ports=[int(p) for p in (row.get("open_ports") or [])],
            banners=banners,
            detected_vulnerabilities=list(row.get("detected_vulnerabilities") or []),
            raw_payload=raw_payload if isinstance(raw_payload, dict) else {},
            rag_doc_path=row.get("rag_doc_path"),
            collected_at=row.get("collected_at") or _utcnow(),
        )

    def _persist_artifact(
        self,
        artifact: ShodanReconArtifact,
        *,
        run_id: UUID | None,
        query: str,
    ) -> None:
        banners_json = json.dumps(
            [b.model_dump(mode="json") for b in artifact.banners],
            ensure_ascii=False,
        )
        self._db.execute(
            """
            INSERT INTO fofa_recon_artifacts (
                artifact_id, request_id, run_id, operator_id, ip_address, query_text,
                hostnames, org, isp, asn, os, country_code, city, open_ports,
                banners, detected_vulnerabilities, raw_payload, rag_doc_path, collected_at
            ) VALUES (
                :artifact_id, :request_id, :run_id, :operator_id, :ip_address, :query_text,
                :hostnames, :org, :isp, :asn, :os, :country_code, :city, :open_ports,
                CAST(:banners AS jsonb), :detected_vulnerabilities,
                CAST(:raw_payload AS jsonb), :rag_doc_path, :collected_at
            )
            ON CONFLICT (artifact_id) DO UPDATE SET
                banners = EXCLUDED.banners,
                open_ports = EXCLUDED.open_ports,
                detected_vulnerabilities = EXCLUDED.detected_vulnerabilities,
                raw_payload = EXCLUDED.raw_payload,
                collected_at = EXCLUDED.collected_at
            """,
            {
                "artifact_id": str(artifact.artifact_id),
                "request_id": str(artifact.request_id),
                "run_id": str(run_id) if run_id else None,
                "operator_id": artifact.operator_id,
                "ip_address": artifact.ip_address,
                "query_text": query,
                "hostnames": artifact.hostnames,
                "org": artifact.org,
                "isp": artifact.isp,
                "asn": artifact.asn,
                "os": artifact.os,
                "country_code": artifact.country_code,
                "city": artifact.city,
                "open_ports": artifact.open_ports,
                "banners": banners_json,
                "detected_vulnerabilities": artifact.detected_vulnerabilities,
                "raw_payload": json.dumps(artifact.raw_payload, ensure_ascii=False),
                "rag_doc_path": artifact.rag_doc_path,
                "collected_at": artifact.collected_at.isoformat(),
            },
        )


class HybridReconModule:
    """Orchestrate FOFA Redis hunting against the authorized desktop target pool."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._fofa = SamsonFofaClient(self._settings)

    async def close(self) -> None:
        await self._fofa.close()

    async def recon_target_pool(
        self,
        *,
        source_root: str | None = None,
        operator_id: str = "operator-alpha",
        run_id: UUID | None = None,
        allow_global_redis_hunt: bool = False,
        force_refresh: bool = False,
        limit: int | None = None,
    ) -> HybridReconResult:
        """Extract IPs from ~/Desktop/тест ЦЕЛИ (or override) and hunt Redis:6379 via FOFA."""
        request_id = uuid4()
        loader = TargetLoader(explicit_root=source_root) if source_root else TargetLoader()
        pool = loader.load()
        ips = self._extract_ips(pool.targets)
        if limit is not None and limit >= 0:
            ips = ips[:limit]

        # Sync FOFA account quota into local budget before spending.
        if (self._settings.fofa_api_key or "").strip():
            try:
                await self._fofa.fetch_account_info()
            except Exception as exc:  # noqa: BLE001
                logger.warning("FOFA account sync failed: %s", exc)

        artifacts: list[ShodanReconArtifact] = []
        queries: list[str] = []
        fofa_lookups = 0
        fofa_cache_hits = 0
        fofa_credits = 0
        blocked = False
        block_reason: str | None = None

        if not ips and allow_global_redis_hunt:
            queries.append(_REDIS_GLOBAL_QUERY)
            result = await self._fofa.search(
                _REDIS_GLOBAL_QUERY,
                operator_id=operator_id,
                request_id=request_id,
                run_id=run_id,
            )
            fofa_lookups += 1
            fofa_credits += result.credits_spent
            if result.from_cache:
                fofa_cache_hits += 1
            if result.is_blocked:
                blocked = True
                block_reason = result.block_reason
            artifacts.extend(result.artifacts)
        else:
            for ip in ips:
                result = await self._fofa.hunt_redis_for_ip(
                    ip,
                    operator_id=operator_id,
                    request_id=request_id,
                    run_id=run_id,
                    force_refresh=force_refresh,
                )
                queries.append(result.query)
                fofa_lookups += 1
                fofa_credits += result.credits_spent
                if result.from_cache:
                    fofa_cache_hits += 1
                if result.is_blocked:
                    blocked = True
                    block_reason = result.block_reason
                    break
                artifacts.extend(result.artifacts)

        redis_candidates = sum(
            1
            for art in artifacts
            if _REDIS_PORT in art.open_ports
            or "EXPOSED_REDIS_6379" in art.detected_vulnerabilities
            or any(b.product == "redis" for b in art.banners)
        )
        return HybridReconResult(
            request_id=request_id,
            operator_id=operator_id,
            source_root=pool.source_root,
            queries=queries,
            targets_considered=len(ips),
            fofa_lookups=fofa_lookups,
            fofa_cache_hits=fofa_cache_hits,
            fofa_credits_spent=fofa_credits,
            redis_candidates=redis_candidates,
            artifacts=artifacts,
            blocked=blocked,
            block_reason=block_reason,
        )

    @staticmethod
    def _extract_ips(targets: Iterable[Any]) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        for target in targets:
            candidates: list[str] = []
            kind = getattr(target, "kind", None)
            if kind == IngestedTargetKind.IP:
                candidates.append(str(target.normalized_value))
            ip_address = getattr(target, "ip_address", None)
            if ip_address:
                candidates.append(str(ip_address))
            for raw in candidates:
                try:
                    ip = str(ipaddress.ip_address(raw.strip()))
                except ValueError:
                    continue
                if ip in seen:
                    continue
                # Skip pure loopback for FOFA (no internet-facing asset).
                if ipaddress.ip_address(ip).is_loopback:
                    continue
                seen.add(ip)
                found.append(ip)
        return found


async def hunt_redis_pool(
    *,
    source_root: str | None = None,
    operator_id: str = "operator-alpha",
    allow_global_redis_hunt: bool = False,
) -> HybridReconResult:
    """Module-level helper used by orchestrator CLI."""
    module = HybridReconModule()
    try:
        return await module.recon_target_pool(
            source_root=source_root,
            operator_id=operator_id,
            allow_global_redis_hunt=allow_global_redis_hunt,
        )
    finally:
        await module.close()
