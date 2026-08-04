"""Production HTTP client with retries, timeouts, TLS verification, and audit logging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import NetworkError

logger = logging.getLogger(__name__)
_SYSTEM_AUDIT_REQUEST_ID = uuid5(NAMESPACE_URL, "samson-http-client")


@dataclass
class AuditHttpContext:
    """Audit metadata attached to each outbound HTTP call."""

    request_id: UUID
    operator_id: str | None = None
    run_id: UUID | None = None
    tool: str = "http_client"
    action: str = "http_request"


class SamsonHttpClient:
    """Synchronous httpx client for arena targets, Ollama, and audited red-team calls."""

    def __init__(self, settings: SamsonSettings | None = None, db: Database | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = db or Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._client = httpx.Client(
            timeout=httpx.Timeout(
                connect=self._settings.http_connect_timeout_sec,
                read=self._settings.http_timeout_sec,
                write=self._settings.http_timeout_sec,
                pool=self._settings.http_connect_timeout_sec,
            ),
            headers={"User-Agent": self._settings.http_user_agent},
            follow_redirects=False,
            verify=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SamsonHttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        content: bytes | None = None,
        expected_status: tuple[int, ...] = (200, 201, 202, 204),
        audit: AuditHttpContext | None = None,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        merged_headers = dict(headers or {})
        start = time.perf_counter()
        audit_payload = {
            "method": method.upper(),
            "url": url,
            "has_json": json is not None,
            "has_content": content is not None,
        }

        for attempt in range(1, self._settings.http_max_retries + 1):
            try:
                response = self._client.request(
                    method=method.upper(),
                    url=url,
                    json=json,
                    headers=merged_headers,
                    params=params,
                    content=content,
                )
                duration_ms = int((time.perf_counter() - start) * 1000)
                self._log_audit(
                    audit=audit,
                    outcome="pass" if response.status_code in expected_status else "error",
                    payload_hash=sha256_payload(audit_payload),
                    duration_ms=duration_ms,
                    extra={"status_code": response.status_code, "url": url, "method": method.upper()},
                )

                if response.status_code in expected_status:
                    return response

                if response.status_code in (429, 502, 503, 504) and attempt < self._settings.http_max_retries:
                    sleep_for = self._settings.http_retry_backoff_sec * attempt
                    logger.warning(
                        "HTTP %s %s -> %s; retry %s/%s in %.1fs",
                        method,
                        url,
                        response.status_code,
                        attempt,
                        self._settings.http_max_retries,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    continue

                raise NetworkError(
                    f"HTTP {response.status_code} from {method} {url}",
                    url=url,
                    method=method,
                    status_code=response.status_code,
                    body=response.text[:2000],
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt >= self._settings.http_max_retries:
                    break
                time.sleep(self._settings.http_retry_backoff_sec * attempt)
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt >= self._settings.http_max_retries:
                    break
                time.sleep(self._settings.http_retry_backoff_sec * attempt)

        duration_ms = int((time.perf_counter() - start) * 1000)
        self._log_audit(
            audit=audit,
            outcome="error",
            payload_hash=sha256_payload(audit_payload),
            duration_ms=duration_ms,
            extra={"url": url, "method": method.upper(), "error": str(last_exc)},
        )
        raise NetworkError(
            f"HTTP request failed after {self._settings.http_max_retries} attempts: {method} {url}",
            url=url,
            method=method,
            error=str(last_exc),
        )

    def _log_audit(
        self,
        *,
        audit: AuditHttpContext | None,
        outcome: str,
        payload_hash: str,
        duration_ms: int,
        extra: dict[str, Any],
    ) -> None:
        if not self._settings.audit_enabled:
            return
        ctx = audit or AuditHttpContext(request_id=_SYSTEM_AUDIT_REQUEST_ID)
        try:
            self._audit.write_redteam_audit(
                request_id=ctx.request_id,
                tool=ctx.tool,
                operator_id=ctx.operator_id,
                action=ctx.action,
                outcome=outcome,
                payload_hash=payload_hash,
                duration_ms=duration_ms,
                run_id=ctx.run_id,
            )
        except Exception as exc:
            logger.error("Failed to write HTTP audit log: %s", exc)

        logger.info(
            "HTTP audit tool=%s operator=%s outcome=%s duration_ms=%s %s",
            ctx.tool,
            ctx.operator_id,
            outcome,
            duration_ms,
            extra,
        )

    def get_json(self, url: str, audit: AuditHttpContext | None = None, **kwargs: Any) -> Any:
        return self.request("GET", url, audit=audit, **kwargs).json()

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        audit: AuditHttpContext | None = None,
        **kwargs: Any,
    ) -> Any:
        response = self.request("POST", url, json=payload, audit=audit, **kwargs)
        if not response.content:
            return {}
        return response.json()


class AsyncSamsonHttpClient:
    """Async httpx client with identical retry semantics and audit logging."""

    def __init__(self, settings: SamsonSettings | None = None, db: Database | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = db or Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=self._settings.http_connect_timeout_sec,
                read=self._settings.http_timeout_sec,
                write=self._settings.http_timeout_sec,
                pool=self._settings.http_connect_timeout_sec,
            ),
            headers={"User-Agent": self._settings.http_user_agent},
            follow_redirects=False,
            verify=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        expected_status: tuple[int, ...] = (200, 201, 202, 204),
        audit: AuditHttpContext | None = None,
    ) -> httpx.Response:
        start = time.perf_counter()
        audit_payload = {"method": method.upper(), "url": url, "has_json": json is not None}
        response = await self._client.request(method.upper(), url, json=json, headers=headers)
        duration_ms = int((time.perf_counter() - start) * 1000)
        ctx = audit or AuditHttpContext(request_id=_SYSTEM_AUDIT_REQUEST_ID)
        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=ctx.request_id,
                tool=ctx.tool,
                operator_id=ctx.operator_id,
                action=ctx.action,
                outcome="pass" if response.status_code in expected_status else "error",
                payload_hash=sha256_payload(audit_payload),
                duration_ms=duration_ms,
                run_id=ctx.run_id,
            )
        if response.status_code not in expected_status:
            raise NetworkError(
                f"HTTP {response.status_code} from {method} {url}",
                url=url,
                method=method,
                status_code=response.status_code,
                body=response.text[:2000],
            )
        return response


class OllamaClient:
    """Ollama embedding and chat API over real HTTP."""

    def __init__(self, settings: SamsonSettings | None = None, http: SamsonHttpClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._http = http or SamsonHttpClient(self._settings)
        self._owns_http = http is None

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def embed(self, text: str) -> list[float]:
        url = f"{self._settings.ollama_base_url_str}/api/embeddings"
        payload = {"model": self._settings.ollama_embed_model, "prompt": text}
        try:
            data = self._http.post_json(url, payload)
        except NetworkError as exc:
            raise NetworkError(
                f"Ollama embedding failed for model {self._settings.ollama_embed_model}",
                model=self._settings.ollama_embed_model,
                error=exc.detail.message,
            ) from exc

        embedding = data.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise NetworkError(
                "Ollama returned empty embedding vector",
                model=self._settings.ollama_embed_model,
                response_keys=list(data.keys()) if isinstance(data, dict) else [],
            )
        return [float(x) for x in embedding]

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        url = f"{self._settings.ollama_base_url_str}/api/chat"
        payload = {
            "model": self._settings.ollama_chat_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        data = self._http.post_json(url, payload)
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise NetworkError("Ollama chat returned empty content", model=self._settings.ollama_chat_model)
        return content.strip()

    def health_check(self) -> dict[str, Any]:
        url = f"{self._settings.ollama_base_url_str}/api/tags"
        return self._http.get_json(url)
