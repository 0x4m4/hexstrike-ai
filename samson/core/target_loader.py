"""Desktop / on-prem target pool ingestion for Samson SBM bulk audits.

Scans the authorized macOS desktop folder (Cyrillic label) with a container
fallback path, extracts unique IPs / domains / URLs from operator documents,
purges structural junk, and keeps only live-validated destinations.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import re
import socket
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
import yaml
from pydantic import BaseModel, Field, HttpUrl, field_validator

from samson.core.errors import ConfigurationError
from samson.redteam.schemas import AdversaryTargetContext, ContinuousAuditRequest

logger = logging.getLogger(__name__)

DESKTOP_TARGET_DIRNAME = "тест ЦЕЛИ"
CONTAINER_FALLBACK_ROOT = Path("/data/pentest/targets")

_TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".xml",
    ".log",
    ".conf",
    ".cfg",
    ".ini",
    ".list",
    ".url",
}

# Internal history / editor / VCS artifacts — never ingested.
_JUNK_NAME_FRAGMENTS = (
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".history",
    ".Trash",
    ".DS_Store",
    "~",
    ".bak",
    ".swp",
    ".tmp",
    ".orig",
    "Thumbs.db",
)

_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)
_EVM_ADDRESS_RE = re.compile(r"(?<![a-fA-F0-9])0x[a-fA-F0-9]{40}(?![a-fA-F0-9])")
_IPV4_RE = re.compile(
    r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d?\d)(?![\w.])"
)
_DOMAIN_RE = re.compile(
    r"(?<![\w./-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})(?::\d{2,5})?(?![\w.-])",
    re.IGNORECASE,
)
_INVALID_TEXT_RE = re.compile(
    r"^(?:null|none|n/?a|undefined|todo|tbd|xxx+|placeholder|junk|test)$",
    re.IGNORECASE,
)

_SKIP_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "example.edu",
    "localhost",
    "localdomain",
    "invalid",
    "test",
}

# Reserved / documentation / non-production TLDs and suffixes.
_JUNK_TLDS = {
    "test",
    "invalid",
    "localhost",
    "local",
    "example",
    "internal",
    "lan",
    "home",
    "corp",
    "localdomain",
}

# RFC 5737 / RFC 3849 documentation + other non-routable junk ranges.
_JUNK_IP_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("233.252.0.0/24"),
    ipaddress.ip_network("255.255.255.255/32"),
)

_HTTP_PORTS = {80, 8080, 8000, 8888, 3000, 5000, 7001, 9000}
_HTTPS_PORTS = {443, 8443, 9443}
_LIVE_PROBE_TIMEOUT_SEC = float(os.environ.get("SAMSON_TARGET_LIVE_TIMEOUT_SEC", "2.0"))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestedTargetKind(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    WEB3 = "web3"


class IngestedWeb3Target(BaseModel):
    """Web3 wallet / contract address extracted for Arkham enrichment."""

    address: str
    checksum: str | None = None
    source_files: list[str] = Field(default_factory=list)


class IngestedTarget(BaseModel):
    """Normalized engagement target extracted from operator documents."""

    target_id: UUID = Field(default_factory=uuid4)
    kind: IngestedTargetKind
    raw_value: str
    normalized_value: str
    source_files: list[str] = Field(default_factory=list)
    ip_address: str | None = None
    domain: str | None = None
    port: int | None = None
    audit_endpoint: HttpUrl | None = None
    interface_type: str = "IBAN-Parser"
    open_ports: list[int] = Field(default_factory=list)
    detected_vulnerabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    web3: IngestedWeb3Target | None = None

    @field_validator("normalized_value")
    @classmethod
    def _strip_normalized(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("normalized_value must be non-empty")
        return text

    def to_adversary_context(
        self,
        *,
        auth_headers: dict[str, str] | None = None,
    ) -> AdversaryTargetContext:
        endpoint = self.audit_endpoint
        if endpoint is None:
            raise ConfigurationError(
                "Ingested target has no audit_endpoint; call resolve_audit_endpoints first",
                target=self.normalized_value,
            )
        return AdversaryTargetContext(
            target_id=self.target_id,
            target_endpoint=endpoint,
            interface_type=self.interface_type,
            auth_headers=dict(auth_headers or {}),
        )

    def to_continuous_audit_request(
        self,
        *,
        operator_id: str,
        scenario_id: str = "bulk-continuous-audit",
        run_id: UUID | None = None,
        auth_headers: dict[str, str] | None = None,
        policy_profile: str = "strict",
        request_id: UUID | None = None,
    ) -> ContinuousAuditRequest:
        endpoint = self.audit_endpoint
        if endpoint is None:
            raise ConfigurationError(
                "Ingested target has no audit_endpoint; call resolve_audit_endpoints first",
                target=self.normalized_value,
            )
        return ContinuousAuditRequest(
            request_id=request_id or uuid4(),
            target_endpoint=endpoint,
            interface_type=self.interface_type,
            operator_id=operator_id,
            scenario_id=scenario_id,
            run_id=run_id,
            auth_headers=dict(auth_headers or {}),
            policy_profile=policy_profile,  # type: ignore[arg-type]
        )


class IngestedTargetPool(BaseModel):
    """Complete pool of unique live-validated targets from one filesystem scan."""

    source_root: str
    scanned_files: int = 0
    skipped_files: int = 0
    dropped_junk: int = 0
    dropped_offline: int = 0
    targets: list[IngestedTarget] = Field(default_factory=list)
    loaded_at: datetime = Field(default_factory=_utcnow)

    @property
    def unique_count(self) -> int:
        return len(self.targets)


class TargetLoader:
    """Scan authorized target folders and emit strict Pydantic target models."""

    def __init__(
        self,
        *,
        desktop_dirname: str = DESKTOP_TARGET_DIRNAME,
        container_fallback: Path | str = CONTAINER_FALLBACK_ROOT,
        explicit_root: Path | str | None = None,
    ) -> None:
        self._desktop_dirname = desktop_dirname
        self._container_fallback = Path(container_fallback).expanduser()
        self._explicit_root = Path(explicit_root).expanduser() if explicit_root else None

    def resolve_source_root(self) -> Path:
        if self._explicit_root is not None:
            root = self._explicit_root
            if not root.is_dir():
                raise ConfigurationError(
                    f"Explicit target root does not exist: {root}",
                    path=str(root),
                )
            return root.resolve()

        desktop_root = Path.home() / "Desktop" / self._desktop_dirname
        if desktop_root.is_dir():
            logger.info("Using macOS desktop target pool: %s", desktop_root)
            return desktop_root.resolve()

        # Some environments expose the same folder via $HOME/Desktop with NFC/NFD variants
        desktop_parent = Path.home() / "Desktop"
        if desktop_parent.is_dir():
            for child in desktop_parent.iterdir():
                if child.is_dir() and child.name.casefold() == self._desktop_dirname.casefold():
                    logger.info("Using desktop target pool (casefold match): %s", child)
                    return child.resolve()

        env_root = os.environ.get("SAMSON_TARGETS_DIR") or os.environ.get("SAMSON_TARGET_POOL_DIR")
        if env_root:
            env_path = Path(env_root).expanduser()
            if env_path.is_dir():
                logger.info("Using SAMSON_TARGETS_DIR target pool: %s", env_path)
                return env_path.resolve()

        if self._container_fallback.is_dir():
            logger.info("Using container fallback target pool: %s", self._container_fallback)
            return self._container_fallback.resolve()

        raise ConfigurationError(
            "No target pool found. Expected "
            f"~/Desktop/{self._desktop_dirname} or {self._container_fallback}",
            desktop=str(desktop_root),
            fallback=str(self._container_fallback),
        )

    def load(self) -> IngestedTargetPool:
        root = self.resolve_source_root()
        files = list(self._iter_document_files(root))
        by_key: dict[str, IngestedTarget] = {}
        scanned = 0
        skipped = 0
        dropped_junk = 0

        for path in files:
            try:
                text = self._read_text(path)
            except OSError as exc:
                logger.warning("Skipping unreadable target document %s: %s", path, exc)
                skipped += 1
                continue
            scanned += 1
            relative = str(path.relative_to(root))
            for kind, value in self.extract_indicators(text):
                reason = self._structural_reject_reason(kind, value)
                if reason:
                    dropped_junk += 1
                    print(f"[-] Dropped junk target: {value} ({reason})", flush=True)
                    logger.info("Dropped junk target %s (%s)", value, reason)
                    continue
                key = f"{kind.value}:{value.lower()}"
                existing = by_key.get(key)
                if existing is not None:
                    if relative not in existing.source_files:
                        existing.source_files.append(relative)
                    continue
                # Host-level duplicate collapse (prefer URL > domain > ip)
                host_key = self._host_dedupe_key(kind, value)
                if host_key:
                    rival_key = next(
                        (
                            k
                            for k, t in by_key.items()
                            if self._host_dedupe_key(t.kind, t.normalized_value) == host_key
                        ),
                        None,
                    )
                    if rival_key is not None:
                        rival = by_key[rival_key]
                        if self._kind_rank(kind) <= self._kind_rank(rival.kind):
                            if relative not in rival.source_files:
                                rival.source_files.append(relative)
                            dropped_junk += 1
                            print(
                                f"[-] Dropped junk target: {value} "
                                f"(duplicate host of {rival.normalized_value})"
                            )
                            continue
                        dropped_junk += 1
                        print(
                            f"[-] Dropped junk target: {rival.normalized_value} "
                            f"(duplicate host superseded by {value})"
                        )
                        del by_key[rival_key]
                by_key[key] = self._build_target(kind, value, source_file=relative)

        candidates = sorted(by_key.values(), key=lambda t: (t.kind.value, t.normalized_value))
        for target in candidates:
            self.resolve_audit_endpoint(target)

        live: list[IngestedTarget] = []
        dropped_offline = 0
        for target in candidates:
            ok, detail = self._probe_live(target)
            if not ok:
                dropped_offline += 1
                print(f"[-] Dropped offline target: {target.normalized_value} ({detail})", flush=True)
                logger.info(
                    "Dropped offline target %s (%s)",
                    target.normalized_value,
                    detail,
                )
                continue
            target.metadata["live_probe"] = detail
            live.append(target)
            endpoint = str(target.audit_endpoint) if target.audit_endpoint else target.normalized_value
            print(f"[+] Active target validated: {endpoint}", flush=True)

        pool = IngestedTargetPool(
            source_root=str(root),
            scanned_files=scanned,
            skipped_files=skipped,
            dropped_junk=dropped_junk,
            dropped_offline=dropped_offline,
            targets=live,
        )
        logger.info(
            "Ingested %s live targets (junk=%s offline=%s) from %s files under %s",
            pool.unique_count,
            pool.dropped_junk,
            pool.dropped_offline,
            pool.scanned_files,
            pool.source_root,
        )
        if not pool.targets:
            raise ConfigurationError(
                "Target pool empty after sanitization — no live validated destinations",
                source_root=pool.source_root,
                dropped_junk=pool.dropped_junk,
                dropped_offline=pool.dropped_offline,
            )
        return pool

    @staticmethod
    def extract_indicators(text: str) -> list[tuple[IngestedTargetKind, str]]:
        found: list[tuple[IngestedTargetKind, str]] = []
        seen: set[str] = set()

        def _add(kind: IngestedTargetKind, value: str) -> None:
            normalized = TargetLoader._normalize_value(kind, value)
            if not normalized:
                return
            key = f"{kind.value}:{normalized.lower()}"
            if key in seen:
                return
            seen.add(key)
            found.append((kind, normalized))

        url_hosts: set[str] = set()
        for match in _URL_RE.finditer(text):
            raw = match.group(0).rstrip(".,;:!?")
            before = len(found)
            _add(IngestedTargetKind.URL, raw)
            if len(found) > before:
                host = urlparse(found[-1][1]).hostname
                if host:
                    url_hosts.add(host.lower())

        for match in _EVM_ADDRESS_RE.finditer(text):
            _add(IngestedTargetKind.WEB3, match.group(0))

        for match in _IPV4_RE.finditer(text):
            raw = match.group(0)
            try:
                ipaddress.IPv4Address(raw)
            except ValueError:
                continue
            # Prefer the richer URL indicator when the same host already appears.
            if raw in url_hosts:
                continue
            _add(IngestedTargetKind.IP, raw)

        for match in _DOMAIN_RE.finditer(text):
            raw = match.group(0).rstrip(".,;:!?")
            host = raw.split(":", 1)[0].lower()
            if host in _SKIP_DOMAINS or any(host == d or host.endswith(f".{d}") for d in _JUNK_TLDS):
                continue
            if host.endswith(".example"):
                continue
            # Skip IPv4 already captured as IP
            if _IPV4_RE.fullmatch(host):
                continue
            # Skip URL hosts already captured
            if host in url_hosts:
                continue
            _add(IngestedTargetKind.DOMAIN, raw)

        return found

    @staticmethod
    def _kind_rank(kind: IngestedTargetKind) -> int:
        return {
            IngestedTargetKind.URL: 3,
            IngestedTargetKind.DOMAIN: 2,
            IngestedTargetKind.IP: 1,
            IngestedTargetKind.WEB3: 4,
        }[kind]

    @staticmethod
    def _host_dedupe_key(kind: IngestedTargetKind, value: str) -> str | None:
        if kind == IngestedTargetKind.WEB3:
            return f"web3:{value.lower()}"
        if kind == IngestedTargetKind.URL:
            host = urlparse(value).hostname
            port = urlparse(value).port
            if not host:
                return None
            return f"{host.lower()}:{port or (443 if value.lower().startswith('https') else 80)}"
        if kind == IngestedTargetKind.DOMAIN:
            host = value.split(":", 1)[0].lower()
            port = int(value.split(":", 1)[1]) if ":" in value and value.rsplit(":", 1)[1].isdigit() else 443
            return f"{host}:{port}"
        if kind == IngestedTargetKind.IP:
            return f"{value}:80"
        return None

    @classmethod
    def _structural_reject_reason(cls, kind: IngestedTargetKind, value: str) -> str | None:
        text = (value or "").strip()
        if not text or text.isspace():
            return "empty"
        if _INVALID_TEXT_RE.match(text):
            return "invalid_text_pattern"
        if kind == IngestedTargetKind.WEB3:
            if not _EVM_ADDRESS_RE.fullmatch(text):
                return "invalid_evm_address"
            if text.lower() == "0x" + ("0" * 40):
                return "zero_address"
            return None
        if kind == IngestedTargetKind.IP:
            try:
                ip = ipaddress.IPv4Address(text)
            except ValueError:
                return "invalid_ipv4"
            for network in _JUNK_IP_NETWORKS:
                if ip in network:
                    return f"documentation_or_reserved_ip:{network}"
            if ip.is_multicast or ip.is_unspecified or ip.is_reserved:
                return "non_routable_ip"
            return None
        if kind == IngestedTargetKind.DOMAIN:
            host = text.split(":", 1)[0].lower()
            labels = host.split(".")
            if len(labels) < 2:
                return "not_fqdn"
            if any(not label or len(label) > 63 for label in labels):
                return "invalid_fqdn_label"
            tld = labels[-1]
            if tld in _JUNK_TLDS or host in _SKIP_DOMAINS:
                return f"junk_tld_or_domain:{tld}"
            if any(host == d or host.endswith(f".{d}") for d in _JUNK_TLDS):
                return "junk_suffix"
            return None
        if kind == IngestedTargetKind.URL:
            parsed = urlparse(text)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return "invalid_url"
            host = (parsed.hostname or "").lower()
            if not host:
                return "url_missing_host"
            if _INVALID_TEXT_RE.match(host):
                return "invalid_text_pattern"
            # IP-literal URL hosts — documentation ranges out; loopback/private need live probe.
            try:
                ip = ipaddress.IPv4Address(host)
                for network in _JUNK_IP_NETWORKS:
                    if ip in network:
                        return f"documentation_or_reserved_ip:{network}"
                if ip.is_multicast or ip.is_unspecified or ip.is_reserved:
                    return "non_routable_ip"
            except ValueError:
                if host == "localhost":
                    return None
                labels = host.split(".")
                if len(labels) < 2:
                    return "url_host_not_fqdn"
                tld = labels[-1]
                if tld in _JUNK_TLDS or any(host.endswith(f".{d}") for d in _JUNK_TLDS):
                    return f"junk_tld_or_domain:{tld}"
                if host in _SKIP_DOMAINS:
                    return "skip_domain"
            return None
        return "unknown_kind"

    @classmethod
    def _probe_live(cls, target: IngestedTarget) -> tuple[bool, str]:
        """Strict live check — HTTP(S) response required for audit destinations."""
        # Web3 addresses are validated structurally; Arkham enrichment is the live check.
        if target.kind == IngestedTargetKind.WEB3:
            return True, "web3_address_structurally_valid"
        endpoint = str(target.audit_endpoint) if target.audit_endpoint else target.normalized_value
        parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
        host = parsed.hostname
        if not host:
            return False, "missing_host"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            with socket.create_connection((host, port), timeout=_LIVE_PROBE_TIMEOUT_SEC):
                pass
        except OSError as exc:
            return False, f"tcp_unreachable:{exc}"

        url = endpoint if "://" in endpoint else f"http://{host}:{port}/"
        try:
            with httpx.Client(
                timeout=_LIVE_PROBE_TIMEOUT_SEC,
                follow_redirects=True,
                verify=False,
            ) as client:
                response = client.request("GET", url)
            # Any completed HTTP exchange (incl. 4xx/5xx) proves an active API/service.
            if response.status_code <= 0:
                return False, "http_invalid_status"
            return True, f"http_{response.status_code}"
        except httpx.TimeoutException:
            return False, "http_timeout_no_response"
        except httpx.HTTPError as exc:
            return False, f"http_unreachable:{type(exc).__name__}"

    @staticmethod
    def resolve_audit_endpoint(
        target: IngestedTarget,
        *,
        preferred_ports: Iterable[int] | None = None,
        interface_type: str = "IBAN-Parser",
    ) -> IngestedTarget:
        """Attach a concrete HTTP(S) audit endpoint for continuous-audit."""
        target.interface_type = interface_type
        ports = list(preferred_ports) if preferred_ports is not None else list(target.open_ports)

        if target.kind == IngestedTargetKind.WEB3:
            # Continuous-audit still needs an HTTP arena endpoint; wallet itself is in metadata.
            from samson.core.config import get_settings

            arena = get_settings().arena_base_url_str.rstrip("/")
            endpoint = f"{arena}/api/v1/arena/financial/transfers"
            target.audit_endpoint = endpoint  # type: ignore[assignment]
            target.web3 = IngestedWeb3Target(
                address=target.normalized_value,
                checksum=target.normalized_value,
                source_files=list(target.source_files),
            )
            target.metadata["web3_address"] = target.normalized_value
            target.metadata["ingested_web3"] = True
            target.interface_type = interface_type
            return target

        if target.kind == IngestedTargetKind.URL:
            target.audit_endpoint = target.normalized_value  # type: ignore[assignment]
            parsed = urlparse(target.normalized_value)
            target.domain = parsed.hostname
            target.port = parsed.port
            if parsed.hostname:
                try:
                    ipaddress.ip_address(parsed.hostname)
                    target.ip_address = parsed.hostname
                except ValueError:
                    pass
            return target

        if target.kind == IngestedTargetKind.DOMAIN:
            host = target.normalized_value
            port: int | None = None
            if ":" in host and not host.startswith("["):
                host_part, port_part = host.rsplit(":", 1)
                if port_part.isdigit():
                    host, port = host_part, int(port_part)
            target.domain = host
            target.port = port
            if port in _HTTPS_PORTS:
                endpoint = f"https://{host}:{port}/"
            elif port:
                endpoint = f"http://{host}:{port}/"
            else:
                endpoint = f"https://{host}/"
            target.audit_endpoint = endpoint  # type: ignore[assignment]
            return target

        # IP
        ip = target.normalized_value
        target.ip_address = ip
        http_port = TargetLoader._pick_http_port(ports)
        target.port = http_port
        if http_port in _HTTPS_PORTS:
            endpoint = f"https://{ip}:{http_port}/"
        elif http_port and http_port not in (80,):
            endpoint = f"http://{ip}:{http_port}/"
        elif http_port == 80:
            endpoint = f"http://{ip}/"
        else:
            endpoint = f"http://{ip}/"
        target.audit_endpoint = endpoint  # type: ignore[assignment]
        return target

    def write_scope_overlay(
        self,
        pool: IngestedTargetPool,
        *,
        base_scope_path: Path | str,
        destination: Path | str,
    ) -> Path:
        """Authorize ingested targets for the bulk-audit engagement window."""
        base_path = Path(base_scope_path)
        if not base_path.is_file():
            raise ConfigurationError(f"Scope config not found: {base_path}", path=str(base_path))
        data = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ConfigurationError("Scope config root must be a mapping", path=str(base_path))

        targets = list(data.get("targets") or [])
        existing_ids = {str(t.get("target_id")) for t in targets if isinstance(t, dict)}
        techniques = [
            "persistence",
            "data_access",
            "lateral_movement",
            "invoice_substitution",
            "payment_api_abuse",
            "beneficiary_swap",
            "llm_payment_injection",
        ]
        agents = ["impact_simulation", "financial_sandbox", "garak", "shodan"]

        for item in pool.targets:
            if item.audit_endpoint is None:
                self.resolve_audit_endpoint(item)
            tid = f"ingested-{item.target_id.hex[:12]}"
            if tid in existing_ids:
                continue
            parsed = urlparse(str(item.audit_endpoint))
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            cidrs: list[str] = []
            if item.ip_address:
                try:
                    ip = ipaddress.ip_address(item.ip_address)
                    cidrs = [str(ipaddress.ip_network(f"{ip}/{ip.max_prefixlen}", strict=False))]
                except ValueError:
                    cidrs = []
            targets.append(
                {
                    "target_id": tid,
                    "base_url": base_url,
                    "allowed_techniques": techniques,
                    "allowed_agents": agents,
                    "network_cidrs": cidrs,
                    "metadata": {
                        "type": "ingested",
                        "kind": item.kind.value,
                        "normalized": item.normalized_value,
                        "source_files": item.source_files,
                    },
                }
            )
            existing_ids.add(tid)

        data["targets"] = targets
        # Ingested desktop pool is an authorized engagement set for this run.
        data["allowed_external_egress"] = True
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        logger.info("Wrote authorized scope overlay with %s targets → %s", len(targets), dest)
        return dest.resolve()

    @staticmethod
    def _pick_http_port(ports: Iterable[int]) -> int | None:
        ordered = list(ports)
        for preferred in (443, 8443, 80, 8080, 8000, 8888, 3000):
            if preferred in ordered:
                return preferred
        for port in ordered:
            if port in _HTTP_PORTS or port in _HTTPS_PORTS:
                return port
        return ordered[0] if ordered else None

    @staticmethod
    def _normalize_value(kind: IngestedTargetKind, value: str) -> str | None:
        text = value.strip().rstrip(".,;:!?")
        if not text:
            return None
        if kind == IngestedTargetKind.URL:
            if text.startswith("//"):
                text = f"http:{text}"
            parsed = urlparse(text)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return None
            path = parsed.path or "/"
            query = f"?{parsed.query}" if parsed.query else ""
            return f"{parsed.scheme}://{parsed.netloc}{path}{query}"
        if kind == IngestedTargetKind.WEB3:
            if not _EVM_ADDRESS_RE.fullmatch(text):
                return None
            return "0x" + text[2:].lower()
        if kind == IngestedTargetKind.IP:
            try:
                return str(ipaddress.IPv4Address(text))
            except ValueError:
                return None
        # domain
        return text.lower()

    @staticmethod
    def _build_target(kind: IngestedTargetKind, value: str, *, source_file: str) -> IngestedTarget:
        ip_address = value if kind == IngestedTargetKind.IP else None
        domain = value.split(":", 1)[0] if kind == IngestedTargetKind.DOMAIN else None
        web3: IngestedWeb3Target | None = None
        if kind == IngestedTargetKind.URL:
            host = urlparse(value).hostname
            domain = host
            if host:
                try:
                    ipaddress.ip_address(host)
                    ip_address = host
                except ValueError:
                    pass
        if kind == IngestedTargetKind.WEB3:
            web3 = IngestedWeb3Target(address=value, checksum=value, source_files=[source_file])
        return IngestedTarget(
            kind=kind,
            raw_value=value,
            normalized_value=value,
            source_files=[source_file],
            ip_address=ip_address,
            domain=domain,
            web3=web3,
            metadata={"web3_address": value, "ingested_web3": True} if kind == IngestedTargetKind.WEB3 else {},
        )

    @staticmethod
    def _iter_document_files(root: Path) -> Iterable[Path]:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue
            joined = str(path)
            if any(fragment in joined for fragment in _JUNK_NAME_FRAGMENTS):
                continue
            name_lower = path.name.lower()
            if name_lower.endswith((".bak", ".swp", ".tmp", ".orig", "~")):
                continue
            if path.suffix.lower() in _TEXT_SUFFIXES or path.suffix == "":
                yield path

    @staticmethod
    def _read_text(path: Path) -> str:
        raw = path.read_bytes()
        if not raw:
            return ""
        # Skip obvious binaries
        if b"\x00" in raw[:2048]:
            raise OSError("binary file")
        for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", errors="replace")

        suffix = path.suffix.lower()
        if suffix == ".json":
            try:
                return json.dumps(json.loads(text), ensure_ascii=False)
            except json.JSONDecodeError:
                return text
        if suffix in {".yaml", ".yml"}:
            try:
                loaded = yaml.safe_load(text)
                return json.dumps(loaded, ensure_ascii=False) if loaded is not None else text
            except yaml.YAMLError:
                return text
        return text
