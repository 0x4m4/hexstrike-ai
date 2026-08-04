"""mcp_rpc_gateway — unified interface for node management."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.core.monitor.mempool import MempoolMonitor, MonitorConfig
from hexstrike.paths import ROOT, RPC_CONFIG

sys.path.insert(0, str(ROOT / "scripts"))
from crypto_rpc_orchestrator import load_config, rpc_with_fallback  # noqa: E402


@dataclass
class RpcGatewayMcp:
    """Unified RPC node management facade for agents and orchestrator."""

    bus: ContextBus
    config_path: Any = RPC_CONFIG
    monitor: MempoolMonitor | None = None

    def __post_init__(self) -> None:
        if self.monitor is None:
            self.monitor = MempoolMonitor(bus=self.bus, config=MonitorConfig(config_path=self.config_path))

    def list_endpoints(self) -> list[str]:
        cfg = load_config(self.config_path)
        return [cfg["primary"], *cfg.get("fallbacks", [])]

    def call(self, method: str, params: list[Any] | None = None, timeout: float = 8.0) -> dict[str, Any]:
        params = params or []
        url, resp = rpc_with_fallback(self.list_endpoints(), method, params, timeout=timeout)
        self.bus.publish("mcp.rpc.call", {"method": method, "rpc": url}, source="mcp_rpc_gateway")
        return {"rpc": url, "response": resp}

    def health(self) -> dict[str, Any]:
        return self.monitor.health() if self.monitor else {"status": "no_monitor"}
