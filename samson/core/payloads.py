"""Payload registry and orchestration for authorized red-team techniques."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from samson.core.config import SamsonSettings, get_settings
from samson.core.errors import PayloadOrchestrationError
from samson.core.http_client import SamsonHttpClient
from samson.core.scope import ScopeEnforcer

logger = logging.getLogger(__name__)


@dataclass
class PayloadDefinition:
    payload_id: str
    technique: str
    method: str
    path_template: str
    headers: dict[str, str]
    body_template: dict[str, Any]
    content_type: str = "application/json"
    expected_status: tuple[int, ...] = (200, 201, 202, 204)
    metadata: dict[str, Any] | None = None


class PayloadRegistry:
    """Loads payload definitions from JSON files in the configured registry directory."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._payloads: dict[str, PayloadDefinition] = {}
        self.reload()

    def reload(self) -> None:
        root = self._settings.payload_registry_path
        self._payloads.clear()
        if not root.exists():
            logger.warning("Payload registry path does not exist: %s", root)
            return
        for path in sorted(root.glob("**/*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise PayloadOrchestrationError(
                    f"Failed to load payload file: {path}",
                    payload_id=str(path),
                    error=str(exc),
                ) from exc
            if isinstance(data, list):
                for item in data:
                    self._register_item(item, source=str(path))
            elif isinstance(data, dict):
                self._register_item(data, source=str(path))

    def _register_item(self, data: dict[str, Any], *, source: str) -> None:
        payload_id = str(data.get("payload_id") or "")
        if not payload_id:
            raise PayloadOrchestrationError("Payload definition missing payload_id", payload_id=source)
        self._payloads[payload_id] = PayloadDefinition(
            payload_id=payload_id,
            technique=str(data.get("technique") or ""),
            method=str(data.get("method") or "POST").upper(),
            path_template=str(data.get("path_template") or "/"),
            headers={str(k): str(v) for k, v in (data.get("headers") or {}).items()},
            body_template=dict(data.get("body_template") or {}),
            content_type=str(data.get("content_type") or "application/json"),
            expected_status=tuple(int(x) for x in (data.get("expected_status") or [200, 201, 202, 204])),
            metadata=dict(data.get("metadata") or {}),
        )

    def get(self, payload_id: str) -> PayloadDefinition:
        payload = self._payloads.get(payload_id)
        if payload is None:
            raise PayloadOrchestrationError(f"Unknown payload_id: {payload_id}", payload_id=payload_id)
        return payload

    def list_for_technique(self, technique: str) -> list[PayloadDefinition]:
        return [p for p in self._payloads.values() if p.technique == technique]

    def list_all(self) -> list[PayloadDefinition]:
        return list(self._payloads.values())

    def list_active(self) -> list[PayloadDefinition]:
        return [
            payload
            for payload in self._payloads.values()
            if (payload.metadata or {}).get("active", True) is not False
        ]


class PayloadOrchestrator:
    """Executes registered payloads against in-scope arena targets with template substitution."""

    def __init__(
        self,
        settings: SamsonSettings | None = None,
        registry: PayloadRegistry | None = None,
        scope: ScopeEnforcer | None = None,
        http: SamsonHttpClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._registry = registry or PayloadRegistry(self._settings)
        self._scope = scope or ScopeEnforcer(self._settings)
        self._http = http or SamsonHttpClient(self._settings)
        self._owns_http = http is None

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def execute(
        self,
        *,
        payload_id: str,
        arena_target_id: str,
        variables: dict[str, Any],
        operator_id: str,
    ) -> dict[str, Any]:
        payload = self._registry.get(payload_id)
        target = self._scope.assert_target(arena_target_id)
        if payload.technique:
            self._scope.assert_technique(payload.technique, target)
        self._scope.assert_operator(operator_id)

        url = self._render_template(f"{target.base_url}{payload.path_template}", variables)
        self._scope.assert_url_in_scope(url)

        body = self._render_object(payload.body_template, variables)
        headers = {**payload.headers, "Content-Type": payload.content_type}

        logger.info(
            "Executing payload %s (%s %s) against target %s",
            payload_id,
            payload.method,
            url,
            arena_target_id,
        )
        response = self._http.request(
            payload.method,
            url,
            json=body if payload.content_type == "application/json" else None,
            headers=headers,
            expected_status=payload.expected_status,
        )
        result: dict[str, Any] = {
            "payload_id": payload_id,
            "technique": payload.technique,
            "url": url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }
        if response.content:
            try:
                result["body"] = response.json()
            except json.JSONDecodeError:
                result["body_text"] = response.text[:8000]
        return result

    @staticmethod
    def _render_template(template: str, variables: dict[str, Any]) -> str:
        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        if "{{" in rendered:
            raise PayloadOrchestrationError(
                f"Unresolved template variables in path: {template}",
                payload_id=template,
            )
        return rendered

    def _render_object(self, obj: Any, variables: dict[str, Any]) -> Any:
        if isinstance(obj, str):
            return self._render_template(obj, variables)
        if isinstance(obj, list):
            return [self._render_object(item, variables) for item in obj]
        if isinstance(obj, dict):
            return {k: self._render_object(v, variables) for k, v in obj.items()}
        return obj
