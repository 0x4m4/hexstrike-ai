"""Authorized engagement scope enforcement loaded from configuration files."""

from __future__ import annotations

import ipaddress
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import yaml

from samson.core.config import SamsonSettings, get_settings
from samson.core.errors import ConfigurationError, ScopeViolationError

logger = logging.getLogger(__name__)


@dataclass
class ScopeTarget:
    target_id: str
    base_url: str
    allowed_techniques: list[str] = field(default_factory=list)
    allowed_agents: list[str] = field(default_factory=list)
    network_cidrs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EngagementScope:
    project: str
    environment: str
    operator_ids: list[str] = field(default_factory=list)
    targets: dict[str, ScopeTarget] = field(default_factory=dict)
    allowed_doc_types: list[str] = field(default_factory=list)
    allowed_external_egress: bool = False
    time_window_utc: dict[str, str] | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path, settings: SamsonSettings) -> EngagementScope:
        if not path.is_file():
            raise ConfigurationError(f"Scope config not found: {path}", path=str(path))
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"Invalid scope YAML: {path}", path=str(path), error=str(exc)) from exc
        if not isinstance(data, dict):
            raise ConfigurationError("Scope config root must be a mapping", path=str(path))

        targets: dict[str, ScopeTarget] = {}
        for entry in data.get("targets") or []:
            if not isinstance(entry, dict) or "target_id" not in entry or "base_url" not in entry:
                raise ConfigurationError("Each scope target requires target_id and base_url")
            target = ScopeTarget(
                target_id=str(entry["target_id"]),
                base_url=str(entry["base_url"]).rstrip("/"),
                allowed_techniques=[str(t) for t in entry.get("allowed_techniques") or []],
                allowed_agents=[str(a) for a in entry.get("allowed_agents") or []],
                network_cidrs=[str(c) for c in entry.get("network_cidrs") or []],
                metadata=dict(entry.get("metadata") or {}),
            )
            targets[target.target_id] = target

        return cls(
            project=str(data.get("project") or settings.project),
            environment=str(data.get("environment") or settings.environment),
            operator_ids=[str(o) for o in data.get("operator_ids") or []],
            targets=targets,
            allowed_doc_types=[str(d) for d in data.get("allowed_doc_types") or []],
            allowed_external_egress=bool(data.get("allowed_external_egress", False)),
            time_window_utc=data.get("time_window_utc"),
            raw=data,
        )


class ScopeEnforcer:
    """Validates operators, targets, URLs, and techniques against engagement scope."""

    def __init__(self, settings: SamsonSettings | None = None, scope: EngagementScope | None = None) -> None:
        self._settings = settings or get_settings()
        self._scope = scope or EngagementScope.from_yaml(self._settings.scope_config_path, self._settings)

    @property
    def scope(self) -> EngagementScope:
        return self._scope

    def reload(self) -> None:
        self._scope = EngagementScope.from_yaml(self._settings.scope_config_path, self._settings)

    def assert_operator(self, operator_id: str, *, request_id: UUID | None = None) -> None:
        if self._scope.operator_ids and operator_id not in self._scope.operator_ids:
            raise ScopeViolationError(
                f"Operator '{operator_id}' not in engagement scope",
                request_id=request_id,
                operator_id=operator_id,
            )

    def assert_target(self, arena_target_id: str, *, request_id: UUID | None = None) -> ScopeTarget:
        target = self._scope.targets.get(arena_target_id)
        if target is None:
            raise ScopeViolationError(
                f"Target '{arena_target_id}' not authorized in scope config",
                request_id=request_id,
                arena_target_id=arena_target_id,
            )
        return target

    def assert_technique(self, technique: str, target: ScopeTarget, *, request_id: UUID | None = None) -> None:
        if target.allowed_techniques and technique not in target.allowed_techniques:
            raise ScopeViolationError(
                f"Technique '{technique}' not allowed for target '{target.target_id}'",
                request_id=request_id,
                technique=technique,
                target_id=target.target_id,
            )

    def assert_url_in_scope(self, url: str, *, request_id: UUID | None = None) -> None:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ScopeViolationError(f"Malformed URL: {url}", request_id=request_id, url=url)

        if not self._scope.allowed_external_egress:
            host = parsed.hostname or ""
            if self._is_public_host(host):
                authorized = any(self._url_matches_target(url, t.base_url) for t in self._scope.targets.values())
                arena_match = url.startswith(self._settings.arena_base_url_str)
                financial_stripe = url.startswith(self._settings.resolve_financial_stripe_url())
                financial_iban = url.startswith(self._settings.resolve_financial_iban_url())
                ollama_match = url.startswith(self._settings.ollama_base_url_str)
                if not (authorized or arena_match or financial_stripe or financial_iban or ollama_match):
                    raise ScopeViolationError(
                        f"URL not in authorized scope: {url}",
                        request_id=request_id,
                        url=url,
                    )

        for target in self._scope.targets.values():
            if self._url_matches_target(url, target.base_url):
                if target.network_cidrs:
                    host = parsed.hostname or ""
                    if not any(self._host_in_cidr(host, cidr) for cidr in target.network_cidrs):
                        raise ScopeViolationError(
                            f"Host '{host}' outside allowed CIDRs {target.network_cidrs}",
                            request_id=request_id,
                            host=host,
                            cidrs=target.network_cidrs,
                        )
                return

    def assert_doc_type(self, doc_type: str, *, request_id: UUID | None = None) -> None:
        if self._scope.allowed_doc_types and doc_type not in self._scope.allowed_doc_types:
            raise ScopeViolationError(
                f"Document type '{doc_type}' not in scope",
                request_id=request_id,
                doc_type=doc_type,
            )

    @staticmethod
    def _url_matches_target(url: str, base_url: str) -> bool:
        return url.startswith(base_url.rstrip("/"))

    @staticmethod
    def _is_public_host(host: str) -> bool:
        if host in ("localhost", "127.0.0.1", "::1"):
            return False
        if re.match(r"^10\.", host) or re.match(r"^192\.168\.", host) or re.match(r"^172\.(1[6-9]|2\d|3[0-1])\.", host):
            return False
        if host.endswith(".svc") or host.endswith(".svc.cluster.local"):
            return False
        return True

    @staticmethod
    def _host_in_cidr(host: str, cidr: str) -> bool:
        try:
            return ipaddress.ip_address(host) in ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return False

    @staticmethod
    def _assert_host_in_cidr(host: str, cidr: str, *, request_id: UUID | None = None) -> None:
        try:
            ip = ipaddress.ip_address(host)
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as exc:
            raise ScopeViolationError(
                f"Invalid CIDR constraint '{cidr}' for host '{host}'",
                request_id=request_id,
                host=host,
                cidr=cidr,
            ) from exc
        if ip not in network:
            raise ScopeViolationError(
                f"Host '{host}' outside allowed CIDR '{cidr}'",
                request_id=request_id,
                host=host,
                cidr=cidr,
            )
