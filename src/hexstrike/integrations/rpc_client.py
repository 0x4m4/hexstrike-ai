"""Stealth-aware RPC client with endpoint failover."""

from __future__ import annotations

import sys
from typing import Any

from hexstrike.core.stealth.transport import StealthConfig, StealthTransport
from hexstrike.paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from crypto_rpc_orchestrator import load_config, normalize_addr  # noqa: E402

__all__ = ["StealthRpcClient", "normalize_addr", "load_config"]


class StealthRpcClient:
    """JSON-RPC client combining stealth transport with primary/fallback endpoints."""

    def __init__(self, config_path: Any, *, stealth: StealthConfig | None = None) -> None:
        self.config_path = config_path
        self.transport = StealthTransport(stealth or StealthConfig())
        self._active: str = ""

    def endpoints(self) -> list[str]:
        cfg = load_config(self.config_path)
        return [cfg["primary"], *cfg.get("fallbacks", [])]

    @property
    def active_rpc(self) -> str:
        return self._active

    def call(self, method: str, params: list[Any] | None = None, timeout: float = 8.0) -> tuple[str, dict[str, Any]]:
        params = params or []
        last_error: Exception | None = None
        for url in self.endpoints():
            try:
                data = self.transport.rpc_call(url, method, params, timeout=timeout)
                if data.get("error"):
                    last_error = RuntimeError(str(data["error"]))
                    continue
                self._active = url
                return url, data
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
        raise RuntimeError(f"All RPC endpoints failed: {last_error}")
