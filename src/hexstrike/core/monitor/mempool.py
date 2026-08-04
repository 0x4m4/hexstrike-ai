"""Mempool monitor wrapping Geth txpool with failover, stealth transport, and ContextBus."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from hexstrike.bus.context_bus import ContextBus
from hexstrike.core.stealth.transport import StealthConfig, StealthTransport
from hexstrike.integrations.rpc_client import StealthRpcClient
from hexstrike.paths import RPC_CONFIG, ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from crypto_rpc_orchestrator import iter_txpool_txs, load_config  # noqa: E402


@dataclass
class MonitorConfig:
    config_path: Path = RPC_CONFIG
    poll_interval: float = 1.0
    rpc_timeout: float = 8.0
    reconnect_delay: float = 5.0
    stealth_enabled: bool = True


@dataclass
class MempoolMonitor:
    """Stream mempool transactions via Geth JSON-RPC with stealth + auto-failover."""

    bus: ContextBus
    config: MonitorConfig = field(default_factory=MonitorConfig)
    _active_rpc: str = ""
    _running: bool = False
    _rpc: StealthRpcClient | None = None

    def __post_init__(self) -> None:
        stealth_cfg = StealthConfig(enabled=self.config.stealth_enabled)
        self._rpc = StealthRpcClient(self.config.config_path, stealth=stealth_cfg)

    def _endpoints(self) -> list[str]:
        cfg = load_config(self.config.config_path)
        return [cfg["primary"], *cfg.get("fallbacks", [])]

    def health(self) -> dict[str, Any]:
        try:
            url, resp = self._rpc.call("eth_chainId", [], timeout=self.config.rpc_timeout)  # type: ignore[union-attr]
            return {
                "status": "ok",
                "active_rpc": url,
                "chain_id": resp.get("result"),
                "stealth": self._rpc.transport.status() if self._rpc else {},  # type: ignore[union-attr]
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc), "endpoints": self._endpoints()}

    def poll_once(self) -> list[dict[str, Any]]:
        try:
            self._active_rpc, resp = self._rpc.call(  # type: ignore[union-attr]
                "txpool_content", [], timeout=self.config.rpc_timeout
            )
        except Exception as exc:
            self.bus.publish(
                "monitor.rpc_error",
                {"error": str(exc), "endpoints": self._endpoints()},
                source="core.monitor",
            )
            raise

        content = resp.get("result") or {}
        txs = list(iter_txpool_txs(content))
        self.bus.publish(
            "monitor.poll",
            {"rpc": self._active_rpc, "tx_count": len(txs), "stealth": True},
            source="core.monitor",
        )
        return txs

    def stream(self, duration_seconds: float | None = None) -> Iterator[dict[str, Any]]:
        """Yield transactions from consecutive mempool polls."""
        self._running = True
        deadline = time.time() + duration_seconds if duration_seconds else None

        while self._running:
            try:
                for tx in self.poll_once():
                    enriched = {**tx, "_rpc": self._active_rpc}
                    self.bus.publish(
                        "monitor.tx",
                        {"hash": tx.get("hash"), "from": tx.get("from"), "to": tx.get("to")},
                        source="core.monitor",
                    )
                    yield enriched
            except Exception:
                time.sleep(self.config.reconnect_delay)
                if deadline and time.time() >= deadline:
                    break
                continue

            if deadline and time.time() >= deadline:
                break
            time.sleep(self.config.poll_interval)

    def stop(self) -> None:
        self._running = False
