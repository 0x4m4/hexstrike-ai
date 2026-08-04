"""Safe transaction broadcaster: gas estimation, slippage guard, sniping profiles."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.integrations.rpc_client import StealthRpcClient
from hexstrike.paths import PENDING_ACTION, RPC_CONFIG, ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from crypto_rpc_orchestrator import load_config  # noqa: E402


@dataclass
class SnipingProfile:
    """Competitive tx parameters for time-sensitive execution."""

    priority_fee_gwei: float = 3.0
    max_fee_multiplier: float = 1.25
    gas_limit_buffer_pct: float = 15.0
    use_fastest_rpc: bool = True


@dataclass
class PreflightResult:
    ok: bool
    gas_estimate: int | None = None
    gas_price_wei: int | None = None
    max_fee_per_gas: int | None = None
    max_priority_fee_per_gas: int | None = None
    recommended_rpc: str | None = None
    max_slippage_bps: int = 50
    sniping_ready: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExecutionBroadcaster:
    """Controlled execution layer — sniping-ready but never auto-broadcasts without approval."""

    bus: ContextBus
    config_path: Any = RPC_CONFIG
    default_slippage_bps: int = 50
    require_approval: bool = True
    sniping: SnipingProfile = field(default_factory=SnipingProfile)
    _rpc: StealthRpcClient | None = None

    def __post_init__(self) -> None:
        self._rpc = StealthRpcClient(self.config_path)

    def _rpc_endpoints(self) -> list[str]:
        cfg = load_config(self.config_path)
        return [cfg["primary"], *cfg.get("fallbacks", [])]

    def preflight(
        self,
        tx: dict[str, Any],
        *,
        max_slippage_bps: int | None = None,
        sniping: bool = False,
    ) -> PreflightResult:
        """Estimate gas and build EIP-1559 fee envelope for sniping when requested."""
        slippage = max_slippage_bps if max_slippage_bps is not None else self.default_slippage_bps
        result = PreflightResult(ok=False, max_slippage_bps=slippage)

        try:
            url, gas_resp = self._rpc.call("eth_estimateGas", [tx], timeout=12.0)  # type: ignore[union-attr]
            result.recommended_rpc = url
            if gas_resp.get("error"):
                result.errors.append(str(gas_resp["error"]))
            else:
                base_gas = int(gas_resp.get("result", "0x0"), 16)
                buffer = 1.0 + (self.sniping.gas_limit_buffer_pct / 100.0 if sniping else 0.05)
                result.gas_estimate = int(base_gas * buffer)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"gas_estimate failed: {exc}")

        try:
            _, price_resp = self._rpc.call("eth_gasPrice", [], timeout=8.0)  # type: ignore[union-attr]
            if price_resp.get("result"):
                result.gas_price_wei = int(price_resp["result"], 16)
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"gas_price unavailable: {exc}")

        if sniping and result.gas_price_wei:
            priority = int(self.sniping.priority_fee_gwei * 1e9)
            result.max_priority_fee_per_gas = priority
            result.max_fee_per_gas = int(result.gas_price_wei * self.sniping.max_fee_multiplier) + priority
            result.sniping_ready = result.ok or not result.errors

        if slippage > 500:
            result.warnings.append(f"slippage {slippage}bps exceeds recommended 500bps cap")

        result.ok = not result.errors
        self.bus.publish(
            "execution.preflight",
            {
                "ok": result.ok,
                "gas_estimate": result.gas_estimate,
                "gas_price_wei": result.gas_price_wei,
                "max_fee_per_gas": result.max_fee_per_gas,
                "sniping_ready": result.sniping_ready,
                "slippage_bps": slippage,
                "errors": result.errors,
            },
            source="core.execution",
        )
        return result

    def queue_for_approval(self, tx: dict[str, Any], *, reason: str = "") -> dict[str, Any]:
        """Write pending action — human-in-the-loop via mcp_execution_gate."""
        payload = {
            "status": "awaiting_operator_review",
            "action": "broadcast_tx",
            "reason": reason,
            "transaction": tx,
            "preflight": None,
        }
        pre = self.preflight(tx)
        payload["preflight"] = {
            "ok": pre.ok,
            "gas_estimate": pre.gas_estimate,
            "gas_price_wei": pre.gas_price_wei,
            "max_fee_per_gas": pre.max_fee_per_gas,
            "sniping_ready": pre.sniping_ready,
            "errors": pre.errors,
        }

        if self.require_approval:
            PENDING_ACTION.parent.mkdir(parents=True, exist_ok=True)
            PENDING_ACTION.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            self.bus.publish("execution.queued", payload, source="core.execution")
            return {"queued": True, "path": str(PENDING_ACTION)}

        return {"queued": False, "reason": "approval_required_disabled"}

    def _pending_approved(self) -> bool:
        """Verify PendingAction file has operator approval."""
        if not PENDING_ACTION.is_file():
            return False
        try:
            data = json.loads(PENDING_ACTION.read_text(encoding="utf-8"))
            return data.get("status") == "approved"
        except (json.JSONDecodeError, OSError):
            return False

    def broadcast(self, signed_tx_hex: str, *, approved: bool = False) -> dict[str, Any]:
        """Broadcast only when explicitly approved via mcp_execution_gate / PendingAction."""
        if self.require_approval and (not approved or not self._pending_approved()):
            self.bus.publish(
                "execution.denied",
                {"reason": "missing_operator_approval", "pending_checked": True},
                source="core.execution",
            )
            return {
                "success": False,
                "error": "Operator approval required — set pending_action.json status to approved",
            }

        endpoints = self._rpc_endpoints()
        try:
            url, resp = self._rpc.call("eth_sendRawTransaction", [signed_tx_hex], timeout=15.0)  # type: ignore[union-attr]
            if resp.get("error"):
                self.bus.publish("execution.failed", resp, source="core.execution")
                return {"success": False, "error": resp["error"], "rpc": url}
            tx_hash = resp.get("result")
            self.bus.publish("execution.broadcast", {"hash": tx_hash, "rpc": url}, source="core.execution")
            return {"success": True, "hash": tx_hash, "rpc": url}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}
