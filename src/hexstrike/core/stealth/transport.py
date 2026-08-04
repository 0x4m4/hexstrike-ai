"""TLS-obfuscated / masked outbound HTTP transport for operator OPSEC."""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from typing import Any

import requests

_DEFAULT_UA_POOL = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Geth/v1.13.0-stable/linux-amd64/go1.21",
    "curl/8.4.0",
)


@dataclass
class StealthConfig:
    enabled: bool = True
    rotate_user_agent: bool = True
    jitter_ms_min: int = 50
    jitter_ms_max: int = 250
    proxy_url: str | None = None
    verify_tls: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class StealthTransport:
    """Mask outbound JSON-RPC traffic via UA rotation, jitter, and optional proxy."""

    config: StealthConfig = field(default_factory=StealthConfig)
    _session: requests.Session = field(default_factory=requests.Session, repr=False)

    def __post_init__(self) -> None:
        proxy = self.config.proxy_url or os.environ.get("HEXSTRIKE_PROXY") or os.environ.get("HTTPS_PROXY")
        if proxy:
            self._session.proxies.update({"http": proxy, "https": proxy})
        self._session.verify = self.config.verify_tls

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Connection": "keep-alive",
        }
        if self.config.rotate_user_agent:
            headers["User-Agent"] = random.choice(_DEFAULT_UA_POOL)
        headers.update(self.config.extra_headers)
        return headers

    def _jitter(self) -> None:
        if not self.config.enabled:
            return
        lo, hi = self.config.jitter_ms_min, self.config.jitter_ms_max
        if hi > 0:
            time.sleep(random.uniform(lo, hi) / 1000.0)

    def post_json(self, url: str, payload: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
        self._jitter()
        resp = self._session.post(url, json=payload, headers=self._headers(), timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"error": {"message": "non_object_response"}}

    def rpc_call(self, url: str, method: str, params: list[Any], timeout: float = 8.0) -> dict[str, Any]:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        return self.post_json(url, payload, timeout=timeout)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "proxy": bool(self._session.proxies),
            "verify_tls": self.config.verify_tls,
            "jitter_ms": [self.config.jitter_ms_min, self.config.jitter_ms_max],
        }
