"""Defensive balance validation for sandbox dummy bot (Step 3 — hardening)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "artifacts" / "sandbox" / "anomaly-alerts.jsonl"


class RpcFetchError(Exception):
    """Direct RPC call failed (timeout, connection, JSON-RPC error)."""

    def __init__(self, url: str, method: str, reason: str, *, kind: str = "rpc_error") -> None:
        self.url = url
        self.method = method
        self.reason = reason
        self.kind = kind
        super().__init__(f"{kind}@{url} {method}: {reason}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_alert(entry: dict[str, Any]) -> None:
    from log_utils import append_jsonl

    append_jsonl(ALERTS, entry)
    try:
        from alert_paging import maybe_page

        maybe_page(entry)
    except Exception:  # noqa: BLE001 — paging must never break detection path
        pass


def rpc_call(url: str, method: str, params: list[Any], timeout: float = 10.0) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except TimeoutError as exc:
        raise RpcFetchError(url, method, str(exc), kind="timeout") from exc
    except urllib.error.URLError as exc:
        kind = "timeout" if isinstance(exc.reason, TimeoutError) else "connection"
        raise RpcFetchError(url, method, str(exc.reason or exc), kind=kind) from exc
    if "error" in data:
        raise RpcFetchError(url, method, str(data["error"]), kind="jsonrpc_error")
    return data["result"]


def fetch_balance(url: str, address: str, *, timeout: float = 10.0) -> int:
    result = rpc_call(url, "eth_getBalance", [address, "latest"], timeout=timeout)
    return int(result, 16)


def fetch_nonce(url: str, address: str, *, timeout: float = 10.0) -> int:
    result = rpc_call(url, "eth_getTransactionCount", [address, "latest"], timeout=timeout)
    return int(result, 16)


@dataclass(frozen=True)
class GuardConfig:
    primary_rpc: str
    direct_rpc: str
    address: str
    enabled: bool
    max_balance_delta_wei: int
    anomaly_stale_timeout_sec: float
    rpc_timeout_sec: float

    @classmethod
    def from_env(cls) -> GuardConfig:
        primary = os.environ.get("RPC_URL", "http://127.0.0.1:8546")
        direct = os.environ.get("DIRECT_RPC_URL", os.environ.get("UPSTREAM_RPC", "http://127.0.0.1:8545"))
        enabled = os.environ.get("HARDENING_ENABLED", "").lower() in ("1", "true", "yes")
        return cls(
            primary_rpc=primary,
            direct_rpc=direct,
            address=os.environ.get("TARGET_WATCH_ADDRESS") or os.environ["BOT_ADDRESS"],
            enabled=enabled,
            max_balance_delta_wei=int(os.environ.get("MAX_BALANCE_DELTA_WEI", "0")),
            anomaly_stale_timeout_sec=float(os.environ.get("ANOMALY_STALE_TIMEOUT_SEC", "120")),
            rpc_timeout_sec=float(os.environ.get("GUARD_RPC_TIMEOUT_SEC", "10")),
        )


@dataclass
class GuardState:
    last_balance: int | None = None
    last_nonce: int | None = None
    last_updated_monotonic: float | None = None


@dataclass(frozen=True)
class BalanceSnapshot:
    primary_wei: int
    direct_wei: int
    delta_wei: int
    within_tolerance: bool

    @property
    def match(self) -> bool:
        return self.within_tolerance


def multi_source_balance(cfg: GuardConfig) -> BalanceSnapshot:
    primary = fetch_balance(cfg.primary_rpc, cfg.address, timeout=cfg.rpc_timeout_sec)
    direct = fetch_balance(cfg.direct_rpc, cfg.address, timeout=cfg.rpc_timeout_sec)
    delta = abs(primary - direct)
    return BalanceSnapshot(
        primary_wei=primary,
        direct_wei=direct,
        delta_wei=delta,
        within_tolerance=delta <= cfg.max_balance_delta_wei,
    )


def detect_rpc_mismatch(cfg: GuardConfig, snapshot: BalanceSnapshot) -> dict[str, Any] | None:
    """Block when proxy and direct balances diverge beyond MAX_BALANCE_DELTA_WEI."""
    if snapshot.within_tolerance:
        return None
    alert = {
        "ts": utc_now(),
        "type": "rpc_mismatch",
        "severity": "critical",
        "primary_wei": snapshot.primary_wei,
        "direct_wei": snapshot.direct_wei,
        "delta_wei": snapshot.delta_wei,
        "max_balance_delta_wei": cfg.max_balance_delta_wei,
        "action": "block_signing",
        "message": "Primary RPC balance differs from direct upstream — possible tampering",
    }
    append_alert(alert)
    return alert


def detect_anomaly_no_onchain_activity(
    cfg: GuardConfig,
    state: GuardState,
    current_balance: int,
) -> dict[str, Any] | None:
    """Flag balance drop without a matching nonce increase on direct RPC.

    Assumptions (sandbox):
    - Any nonce increase on direct RPC implies legitimate on-chain activity from this wallet.
      Multiple txs in one poll interval still satisfy the check (nonce strictly increased).
    - We cannot detect partial drains where nonce unchanged (e.g. incoming transfers only).
    - First poll after startup/restart skips this check (last_balance/last_nonce unset).
    - If state is older than ANOMALY_STALE_TIMEOUT_SEC, skip to avoid stale comparisons
      after bot crash/restart mid-session.
    """
    if state.last_balance is None or state.last_nonce is None or state.last_updated_monotonic is None:
        return None

    age_sec = time.monotonic() - state.last_updated_monotonic
    if age_sec > cfg.anomaly_stale_timeout_sec:
        return None

    if current_balance >= state.last_balance:
        return None

    current_nonce = fetch_nonce(cfg.direct_rpc, cfg.address, timeout=cfg.rpc_timeout_sec)
    # Nonce increase of any amount → assume legitimate on-chain drain; partial drains not detected.
    if current_nonce > state.last_nonce:
        return None

    alert = {
        "ts": utc_now(),
        "type": "anomaly_no_onchain_activity",
        "severity": "high",
        "prev_balance_wei": state.last_balance,
        "current_balance_wei": current_balance,
        "nonce": current_nonce,
        "prev_nonce": state.last_nonce,
        "state_age_sec": round(age_sec, 2),
        "action": "block_signing",
        "message": "Balance dropped but no new tx from wallet on direct RPC",
    }
    append_alert(alert)
    return alert


def pre_sign_verify(cfg: GuardConfig, threshold_wei: int) -> tuple[bool, dict[str, Any]]:
    """Allow signing only when direct RPC confirms balance below threshold.

    Distinguishes RPC unreachable/timeout from threshold rejection so operators
    can tell source-of-truth failures apart from proxy false triggers.
    """
    detail: dict[str, Any] = {
        "ts": utc_now(),
        "type": "pre_sign_verify",
        "threshold_wei": threshold_wei,
        "direct_rpc": cfg.direct_rpc,
    }

    try:
        direct_bal = fetch_balance(cfg.direct_rpc, cfg.address, timeout=cfg.rpc_timeout_sec)
    except RpcFetchError as exc:
        detail.update(
            {
                "allowed": False,
                "outcome": "direct_rpc_unavailable",
                "error_kind": exc.kind,
                "error": exc.reason,
                "severity": "critical",
                "action": "block_signing",
                "message": "Direct RPC unreachable — cannot verify trigger (fail closed)",
            }
        )
        append_alert(detail)
        return False, detail

    ok = direct_bal < threshold_wei
    detail.update({"direct_wei": direct_bal, "allowed": ok, "outcome": "verified" if ok else "threshold_rejected"})

    if not ok:
        detail.update(
            {
                "severity": "critical",
                "action": "block_signing",
                "message": "Direct RPC balance above threshold — proxy trigger rejected",
            }
        )
        append_alert(detail)

    return ok, detail


def evaluate_poll(cfg: GuardConfig, state: GuardState) -> dict[str, Any]:
    """Run defensive checks; return decision payload for bot event log.

    First failure wins for block_reason (mismatch is checked before anomaly).
    """
    snapshot = multi_source_balance(cfg)
    checks: dict[str, Any] = {
        "hardening": True,
        "primary_wei": snapshot.primary_wei,
        "direct_wei": snapshot.direct_wei,
        "delta_wei": snapshot.delta_wei,
        "max_balance_delta_wei": cfg.max_balance_delta_wei,
        "balances_match": snapshot.within_tolerance,
        "use_balance_wei": snapshot.direct_wei,
        "block_signing": False,
        "block_reason": None,
        "alerts": [],
    }

    mismatch = detect_rpc_mismatch(cfg, snapshot)
    if mismatch:
        checks["block_signing"] = True
        checks["block_reason"] = "rpc_mismatch"
        checks["alerts"].append(mismatch)
        checks["use_balance_wei"] = snapshot.direct_wei

    anomaly = detect_anomaly_no_onchain_activity(cfg, state, snapshot.direct_wei)
    if anomaly:
        checks["block_signing"] = True
        # Preserve first (most critical) block_reason — mismatch wins over anomaly.
        checks["block_reason"] = checks["block_reason"] or "anomaly_no_onchain_activity"
        checks["alerts"].append(anomaly)

    state.last_balance = snapshot.direct_wei
    state.last_nonce = fetch_nonce(cfg.direct_rpc, cfg.address, timeout=cfg.rpc_timeout_sec)
    state.last_updated_monotonic = time.monotonic()
    return checks
