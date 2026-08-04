"""CoinStats public wallet OSINT client (read-only).

Official API:
  Base: ``https://api.coinstats.app/v1``
  Auth: ``X-API-KEY`` header
  Docs: https://coinstats.app/docs/authentication.md
        https://coinstats.app/api-docs/wallet/other-chains/

Endpoints used:
  GET  /wallet/blockchains
  GET  /wallet/balance?address=&connectionId=
  PATCH /wallet/transactions?address=&connectionId=   (sync)
  GET  /wallet/transactions?address=&connectionId=
  GET  /wallet/defi?address=&connectionId=             (optional)

Policy: public address monitoring / OSINT only — no signing, no drain, no private keys.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ConfigurationError, NetworkError
from samson.redteam.schemas import (
    CoinStatsCollectResult,
    CoinStatsTokenBalance,
    CoinStatsWalletArtifact,
)

logger = logging.getLogger(__name__)

# Source: https://coinstats.app/api-docs/wallet/other-chains/ (credit table)
_CREDITS_BALANCE = 40
_CREDITS_TX_SYNC = 50
_CREDITS_TX_GET = 30
_CREDITS_CHAINS = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_balance_row(row: dict[str, Any], *, connection_id: str) -> CoinStatsTokenBalance:
    """Map CoinStats token object → ``CoinStatsTokenBalance``."""
    amount = _as_float(row.get("amount")) or 0.0
    price = _as_float(row.get("price") if row.get("price") is not None else row.get("priceUsd"))
    value = _as_float(row.get("value") if row.get("value") is not None else row.get("valueUsd"))
    if value is None and price is not None:
        value = amount * price
    return CoinStatsTokenBalance(
        coin_id=str(row.get("coinId") or row.get("id") or "") or None,
        name=str(row.get("name") or "") or None,
        symbol=str(row.get("symbol") or "") or None,
        amount=amount,
        price_usd=price,
        value_usd=value,
        chain=str(row.get("chain") or connection_id) or connection_id,
        raw=dict(row),
    )


class CoinStatsClient:
    """Async CoinStats wallet client: cache-first → rate-limit → live GET."""

    def __init__(
        self,
        settings: SamsonSettings | None = None,
        *,
        api_key: str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._api_key = (api_key or self._settings.coinstats_api_key or "").strip()
        self._base_url = str(self._settings.coinstats_api_base_url).rstrip("/")
        self._min_interval = float(self._settings.coinstats_min_interval_sec)
        self._cache_ttl = int(self._settings.coinstats_cache_ttl_sec)
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._client: httpx.AsyncClient | None = None
        self._rate_lock = asyncio.Lock()
        self._last_query_monotonic: float | None = None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _http(self) -> httpx.AsyncClient:
        if not self._api_key:
            raise ConfigurationError(
                "CoinStats API key missing — set SAMSON_COINSTATS_API_KEY or COINSTATS_API_KEY"
            )
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"X-API-KEY": self._api_key, "Accept": "application/json"},
                timeout=httpx.Timeout(45.0, connect=10.0),
            )
        return self._client

    async def _enforce_rate_limit(self) -> None:
        async with self._rate_lock:
            now = time.monotonic()
            if self._last_query_monotonic is not None:
                wait = self._min_interval - (now - self._last_query_monotonic)
                if wait > 0:
                    await asyncio.sleep(wait)
            self._last_query_monotonic = time.monotonic()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        client = await self._http()
        await self._enforce_rate_limit()
        try:
            response = await client.request(method, path, params=params)
        except httpx.HTTPError as exc:
            raise NetworkError(f"CoinStats request failed: {exc}") from exc
        if response.status_code == 401:
            raise ConfigurationError("CoinStats API key invalid or unauthorized (401)")
        if response.status_code >= 400:
            raise NetworkError(
                f"CoinStats HTTP {response.status_code}: {response.text[:400]}"
            )
        if not response.content:
            return None
        return response.json()

    async def list_blockchains(self) -> list[dict[str, Any]]:
        """GET /wallet/blockchains — supported chains (1 credit)."""
        data = await self._request("GET", "/wallet/blockchains")
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if isinstance(data, dict) and isinstance(data.get("result"), list):
            return [row for row in data["result"] if isinstance(row, dict)]
        return []

    async def get_balance(
        self,
        address: str,
        *,
        connection_id: str,
    ) -> list[CoinStatsTokenBalance]:
        """GET /wallet/balance?address=&connectionId= (40 credits)."""
        addr = (address or "").strip()
        chain = (connection_id or "").strip()
        if not addr or not chain:
            raise ConfigurationError("address and connection_id are required")
        data = await self._request(
            "GET",
            "/wallet/balance",
            params={"address": addr, "connectionId": chain},
        )
        rows: list[Any]
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("result") or data.get("balances") or data.get("data") or []
            if not isinstance(rows, list):
                rows = []
        else:
            rows = []
        return [
            normalize_balance_row(row, connection_id=chain)
            for row in rows
            if isinstance(row, dict)
        ]

    async def sync_transactions(
        self,
        address: str,
        *,
        connection_id: str,
    ) -> Any:
        """PATCH /wallet/transactions — index latest txs before read (50 credits)."""
        return await self._request(
            "PATCH",
            "/wallet/transactions",
            params={
                "address": (address or "").strip(),
                "connectionId": (connection_id or "").strip(),
            },
        )

    async def get_transactions(
        self,
        address: str,
        *,
        connection_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """GET /wallet/transactions (30 credits). Prefer sync_transactions first."""
        data = await self._request(
            "GET",
            "/wallet/transactions",
            params={
                "address": (address or "").strip(),
                "connectionId": (connection_id or "").strip(),
                "limit": max(1, min(int(limit), 100)),
            },
        )
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if isinstance(data, dict):
            for key in ("result", "transactions", "data", "items"):
                rows = data.get(key)
                if isinstance(rows, list):
                    return [row for row in rows if isinstance(row, dict)]
        return []

    async def get_defi(
        self,
        address: str,
        *,
        connection_id: str,
    ) -> Any:
        """GET /wallet/defi — staking/LP/yield when available."""
        return await self._request(
            "GET",
            "/wallet/defi",
            params={
                "address": (address or "").strip(),
                "connectionId": (connection_id or "").strip(),
            },
        )

    def _cache_get(
        self, address: str, connection_id: str
    ) -> CoinStatsWalletArtifact | None:
        row = self._db.fetchone(
            """
            SELECT artifact_id, request_id, operator_id, address, connection_id,
                   is_empty, token_count, total_value_usd, transactions_synced,
                   transaction_count, from_cache, raw_payload, collected_at
            FROM coinstats_wallet_artifacts
            WHERE LOWER(address) = LOWER(:address)
              AND connection_id = :connection_id
              AND collected_at >= NOW() - (:ttl * INTERVAL '1 second')
            ORDER BY collected_at DESC
            LIMIT 1
            """,
            {
                "address": address,
                "connection_id": connection_id,
                "ttl": int(self._cache_ttl),
            },
        )
        if not row:
            return None
        payload = row.get("raw_payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        balances_raw = payload.get("balances") if isinstance(payload, dict) else []
        balances = [
            normalize_balance_row(item, connection_id=connection_id)
            for item in (balances_raw or [])
            if isinstance(item, dict)
        ]
        txs = []
        if isinstance(payload, dict) and isinstance(payload.get("transactions"), list):
            txs = [t for t in payload["transactions"] if isinstance(t, dict)]
        return CoinStatsWalletArtifact(
            artifact_id=UUID(str(row["artifact_id"])),
            request_id=UUID(str(row["request_id"])),
            operator_id=str(row["operator_id"]),
            address=str(row["address"]),
            connection_id=str(row["connection_id"]),
            is_empty=bool(row["is_empty"]),
            token_count=int(row["token_count"] or 0),
            total_value_usd=float(row["total_value_usd"] or 0),
            balances=balances,
            transactions_synced=bool(row["transactions_synced"]),
            transaction_count=int(row["transaction_count"] or 0),
            transactions=txs,
            from_cache=True,
            raw_payload=payload if isinstance(payload, dict) else {},
            collected_at=row["collected_at"] or _utcnow(),
        )

    def _persist(
        self,
        artifact: CoinStatsWalletArtifact,
        *,
        run_id: UUID | None,
    ) -> None:
        self._db.execute(
            """
            INSERT INTO coinstats_wallet_artifacts (
                artifact_id, request_id, run_id, operator_id, address, connection_id,
                is_empty, token_count, total_value_usd, transactions_synced,
                transaction_count, from_cache, raw_payload, collected_at
            ) VALUES (
                :artifact_id, :request_id, :run_id, :operator_id, :address, :connection_id,
                :is_empty, :token_count, :total_value_usd, :transactions_synced,
                :transaction_count, :from_cache, CAST(:raw_payload AS jsonb), :collected_at
            )
            ON CONFLICT (artifact_id) DO NOTHING
            """,
            {
                "artifact_id": str(artifact.artifact_id),
                "request_id": str(artifact.request_id),
                "run_id": str(run_id) if run_id else None,
                "operator_id": artifact.operator_id,
                "address": artifact.address,
                "connection_id": artifact.connection_id,
                "is_empty": artifact.is_empty,
                "token_count": artifact.token_count,
                "total_value_usd": artifact.total_value_usd,
                "transactions_synced": artifact.transactions_synced,
                "transaction_count": artifact.transaction_count,
                "from_cache": False,
                "raw_payload": json.dumps(artifact.raw_payload, ensure_ascii=False, default=str),
                "collected_at": artifact.collected_at.isoformat(),
            },
        )
        # Mirror non-empty / notable wallets into web3_recon for guardrail correlation.
        if not artifact.is_empty or artifact.total_value_usd > 0:
            try:
                self._db.execute(
                    """
                    INSERT INTO web3_recon_artifacts (
                        artifact_id, request_id, run_id, operator_id, address,
                        risk_level, is_risk, entity_name, entity_id, entity_type,
                        label_name, chains_seen, labels, from_cache, raw_payload,
                        rag_doc_path, collected_at
                    ) VALUES (
                        :artifact_id, :request_id, :run_id, :operator_id, :address,
                        'low', FALSE, 'CoinStatsWallet', 'coinstats-wallet', 'wallet',
                        'CoinStats OSINT Snapshot', :chains, :labels, FALSE,
                        CAST(:raw_payload AS jsonb), NULL, :collected_at
                    )
                    ON CONFLICT (artifact_id) DO NOTHING
                    """,
                    {
                        "artifact_id": str(uuid4()),
                        "request_id": str(artifact.request_id),
                        "run_id": str(run_id) if run_id else None,
                        "operator_id": artifact.operator_id,
                        "address": artifact.address,
                        "chains": [artifact.connection_id],
                        "labels": ["coinstats", "wallet_osint", artifact.connection_id],
                        "raw_payload": json.dumps(
                            {
                                "source": "coinstats",
                                "is_empty": artifact.is_empty,
                                "token_count": artifact.token_count,
                                "total_value_usd": artifact.total_value_usd,
                            },
                            ensure_ascii=False,
                        ),
                        "collected_at": artifact.collected_at.isoformat(),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("web3_recon mirror skipped: %s", exc)

    async def lookup_wallet(
        self,
        address: str,
        *,
        connection_id: str,
        operator_id: str = "operator-alpha",
        request_id: UUID | None = None,
        run_id: UUID | None = None,
        force_refresh: bool = False,
        sync_transactions: bool = False,
        include_transactions: bool = False,
        include_defi: bool = False,
        tx_limit: int = 20,
    ) -> CoinStatsCollectResult:
        """Cache-first wallet snapshot for public OSINT monitoring."""
        request_id = request_id or uuid4()
        addr = (address or "").strip()
        chain = (connection_id or "").strip()
        if not addr or not chain:
            raise ConfigurationError("address and connection_id are required")

        if not force_refresh:
            cached = await asyncio.to_thread(self._cache_get, addr, chain)
            if cached is not None:
                return CoinStatsCollectResult(
                    request_id=request_id,
                    address=addr,
                    connection_id=chain,
                    artifact=cached,
                    from_cache=True,
                    credits_hint=0,
                )

        credits = _CREDITS_BALANCE
        balances = await self.get_balance(addr, connection_id=chain)
        total_usd = sum(float(b.value_usd or 0.0) for b in balances)
        non_dust = [b for b in balances if (b.amount or 0) > 0]
        is_empty = len(non_dust) == 0 or total_usd <= 0

        txs: list[dict[str, Any]] = []
        synced = False
        if sync_transactions or include_transactions:
            await self.sync_transactions(addr, connection_id=chain)
            synced = True
            credits += _CREDITS_TX_SYNC
        if include_transactions:
            txs = await self.get_transactions(
                addr, connection_id=chain, limit=tx_limit
            )
            credits += _CREDITS_TX_GET

        defi_raw: Any = None
        if include_defi:
            try:
                defi_raw = await self.get_defi(addr, connection_id=chain)
            except (NetworkError, ConfigurationError) as exc:
                logger.info("CoinStats DeFi unavailable for %s: %s", addr, exc)

        artifact = CoinStatsWalletArtifact(
            artifact_id=uuid4(),
            request_id=request_id,
            operator_id=operator_id,
            address=addr,
            connection_id=chain,
            is_empty=is_empty,
            token_count=len(non_dust),
            total_value_usd=round(total_usd, 6),
            balances=balances,
            transactions_synced=synced,
            transaction_count=len(txs),
            transactions=txs,
            defi_raw=defi_raw,
            from_cache=False,
            raw_payload={
                "balances": [b.raw for b in balances],
                "transactions": txs,
                "defi": defi_raw,
                "credits_hint": credits,
            },
        )
        await asyncio.to_thread(self._persist, artifact, run_id=run_id)

        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=request_id,
                tool="coinstats_wallet",
                operator_id=operator_id,
                action="lookup_wallet",
                outcome="pass",
                payload_hash=sha256_payload(
                    {
                        "address": addr,
                        "connection_id": chain,
                        "is_empty": is_empty,
                        "token_count": artifact.token_count,
                        "total_value_usd": artifact.total_value_usd,
                    }
                ),
                duration_ms=0,
                run_id=run_id,
            )

        logger.info(
            "CoinStats wallet address=%s chain=%s empty=%s tokens=%s usd=%.4f",
            addr,
            chain,
            is_empty,
            artifact.token_count,
            artifact.total_value_usd,
        )
        return CoinStatsCollectResult(
            request_id=request_id,
            address=addr,
            connection_id=chain,
            artifact=artifact,
            from_cache=False,
            credits_hint=credits,
        )
