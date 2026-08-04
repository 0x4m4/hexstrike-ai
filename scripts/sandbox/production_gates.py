"""Phase 0 production gates — fail-closed controls for the rescue money circuit.

Implements GO-LIVE Phase 0 requirements:
- destination/funder allowlist (attack #06)
- TOCTOU: intent hash, nonce lock, post-sign recheck, single-flight dedup
- multi-RPC quorum (2/3 agreement on balance + nonce)
- tx limits, cooldown, kill switch
- operational phases: shadow (read-only), canary, limited

LOCAL SANDBOX / STAGING ONLY — never bypasses mainnet policy in samson.core.config.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from balance_guard import RpcFetchError, append_alert, fetch_balance, fetch_nonce, rpc_call, utc_now


class OperationalPhase(str, Enum):
    LAB = "lab"
    SHADOW = "shadow"
    CANARY = "canary"
    LIMITED = "limited"


class SignerBackend(str, Enum):
    LOCAL_KEY = "local_key"
    KMS = "kms"
    HSM = "hsm"


def _norm_addr(addr: str) -> str:
    return addr.strip().lower()


def parse_csv_addresses(raw: str) -> frozenset[str]:
    items = {_norm_addr(part) for part in raw.split(",") if part.strip()}
    return frozenset(items)


POLICY_VERSION_DEFAULT = "v1"


def compute_intent_hash(
    *,
    to: str,
    value_wei: int,
    data: str = "0x",
    chain_id: int,
    nonce: int,
    policy_version: str = POLICY_VERSION_DEFAULT,
) -> str:
    """Canonical intent hash: H(chainId,to,value,data,nonce,policyVersion)."""
    payload = {
        "chainId": chain_id,
        "to": _norm_addr(to),
        "value": str(value_wei),
        "data": data if data.startswith("0x") else f"0x{data}",
        "nonce": nonce,
        "policyVersion": policy_version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class ProductionGateConfig:
    phase: OperationalPhase
    allowed_funders: frozenset[str]
    allowed_destinations: frozenset[str]
    quorum_urls: tuple[str, ...]
    quorum_min_agree: int
    kill_switch: bool
    max_rescues_per_window: int
    rescue_window_sec: float
    cooldown_after_block_sec: float
    canary_max_value_wei: int
    limited_max_value_wei: int
    signer_backend: SignerBackend
    require_kms_outside_lab: bool
    require_allowlist: bool
    rpc_timeout_sec: float

    @classmethod
    def from_env(cls) -> ProductionGateConfig:
        phase_raw = os.environ.get("GO_LIVE_PHASE", "lab").strip().lower()
        try:
            phase = OperationalPhase(phase_raw)
        except ValueError:
            phase = OperationalPhase.LAB

        funder_raw = os.environ.get("ALLOWED_FUNDERS", "")
        dest_raw = os.environ.get("ALLOWED_DESTINATIONS", "")
        funders = parse_csv_addresses(funder_raw) if funder_raw else frozenset()
        destinations = parse_csv_addresses(dest_raw) if dest_raw else funders

        quorum_raw = os.environ.get("QUORUM_RPC_URLS", os.environ.get("DIRECT_RPC_URL", ""))
        urls = tuple(u.strip() for u in quorum_raw.split(",") if u.strip())
        if not urls:
            primary = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
            direct = os.environ.get("DIRECT_RPC_URL", primary)
            urls = tuple(dict.fromkeys([direct, primary]))

        signer_raw = os.environ.get("SIGNER_BACKEND", "local_key").strip().lower()
        try:
            signer_backend = SignerBackend(signer_raw)
        except ValueError:
            signer_backend = SignerBackend.LOCAL_KEY

        # Outside lab: empty allowlist is a bypass — fail closed by default.
        require_default = "false" if phase == OperationalPhase.LAB else "true"
        require_allowlist = os.environ.get("REQUIRE_ALLOWLIST", require_default).lower() in (
            "1",
            "true",
            "yes",
        )

        return cls(
            phase=phase,
            allowed_funders=funders,
            allowed_destinations=destinations,
            quorum_urls=urls,
            quorum_min_agree=int(os.environ.get("QUORUM_MIN_AGREE", "2")),
            kill_switch=os.environ.get("KILL_SWITCH", "").lower() in ("1", "true", "yes"),
            max_rescues_per_window=int(os.environ.get("MAX_RESCUES_PER_WINDOW", "3")),
            rescue_window_sec=float(os.environ.get("RESCUE_WINDOW_SEC", "3600")),
            cooldown_after_block_sec=float(os.environ.get("COOLDOWN_AFTER_BLOCK_SEC", "300")),
            canary_max_value_wei=int(os.environ.get("CANARY_MAX_VALUE_WEI", "1000000000000000")),
            limited_max_value_wei=int(os.environ.get("LIMITED_MAX_VALUE_WEI", "10000000000000000")),
            signer_backend=signer_backend,
            require_kms_outside_lab=os.environ.get("REQUIRE_KMS_OUTSIDE_LAB", "true").lower()
            in ("1", "true", "yes"),
            require_allowlist=require_allowlist,
            rpc_timeout_sec=float(os.environ.get("GUARD_RPC_TIMEOUT_SEC", "10")),
        )


@dataclass
class RateLimitState:
    attempts: list[float] = field(default_factory=list)
    blocked_until: float = 0.0


class TxRateLimiter:
    def __init__(self, cfg: ProductionGateConfig) -> None:
        self._cfg = cfg
        self._state = RateLimitState()

    def check(self) -> tuple[bool, str | None]:
        now = time.monotonic()
        if now < self._state.blocked_until:
            return False, "cooldown_active"
        window_start = now - self._cfg.rescue_window_sec
        self._state.attempts = [t for t in self._state.attempts if t >= window_start]
        if len(self._state.attempts) >= self._cfg.max_rescues_per_window:
            return False, "rate_limit_exceeded"
        return True, None

    def record_attempt(self) -> None:
        self._state.attempts.append(time.monotonic())

    def record_block(self) -> None:
        self._state.blocked_until = time.monotonic() + self._cfg.cooldown_after_block_sec


class NonceLock:
    """Single-flight mutex per bot address — serializes nonce fetch + sign."""

    _locks: dict[str, threading.Lock] = {}
    _guard = threading.Lock()

    @classmethod
    def for_address(cls, address: str) -> threading.Lock:
        key = _norm_addr(address)
        with cls._guard:
            if key not in cls._locks:
                cls._locks[key] = threading.Lock()
            return cls._locks[key]


class IntentRegistry:
    """Dedup by intent_hash + nonce."""

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._lock = threading.Lock()

    def claim(self, intent_hash: str, nonce: int) -> bool:
        key = f"{intent_hash}:{nonce}"
        with self._lock:
            if key in self._seen:
                return False
            self._seen.add(key)
            return True

    def release(self, intent_hash: str, nonce: int) -> None:
        key = f"{intent_hash}:{nonce}"
        with self._lock:
            self._seen.discard(key)


def _block_compromised(reason: str, dest: str, fund: str, message: str) -> tuple[bool, str]:
    alert = {
        "ts": utc_now(),
        "type": "BLOCK_COMPROMISED_FUNDER",
        "severity": "critical",
        "action": "block_signing",
        "reason": reason,
        "destination": dest,
        "funder": fund,
        "message": message,
    }
    append_alert(alert)
    return False, "BLOCK_COMPROMISED_FUNDER"


def check_allowlist(cfg: ProductionGateConfig, funder: str, destination: str) -> tuple[bool, str | None]:
    """Attack #06 — destination + funder allowlists; fail-closed when required."""
    dest = _norm_addr(destination)
    fund = _norm_addr(funder)

    if not cfg.allowed_funders and not cfg.allowed_destinations:
        if cfg.require_allowlist:
            return _block_compromised(
                "allowlist_empty",
                dest,
                fund,
                "Empty allowlist — fail closed (attack #06 bypass denied)",
            )
        return True, None

    # Both lists must pass when present; destination defaults to funder list in from_env.
    if cfg.allowed_destinations and dest not in cfg.allowed_destinations:
        return _block_compromised(
            "destination_not_allowlisted",
            dest,
            fund,
            "Destination not in allowlist — possible compromised funder (#06)",
        )
    if cfg.allowed_funders and fund not in cfg.allowed_funders:
        return _block_compromised(
            "funder_not_allowlisted",
            dest,
            fund,
            "Funder not in allowlist — compromised funder (#06)",
        )
    return True, None


def check_signer_policy(cfg: ProductionGateConfig) -> tuple[bool, str | None]:
    if cfg.phase == OperationalPhase.SHADOW:
        return False, "shadow_mode_no_sign"
    if cfg.kill_switch:
        return False, "kill_switch_active"
    if cfg.require_kms_outside_lab and cfg.phase != OperationalPhase.LAB:
        if cfg.signer_backend not in (SignerBackend.KMS, SignerBackend.HSM):
            return False, "kms_required_outside_lab"
    if cfg.signer_backend == SignerBackend.LOCAL_KEY and cfg.phase not in (
        OperationalPhase.LAB,
        OperationalPhase.CANARY,
    ):
        raw_key = os.environ.get("BOT_PRIVATE_KEY", "") or os.environ.get("AGENT_PRIVATE_KEY", "")
        if raw_key and cfg.phase == OperationalPhase.LIMITED:
            return False, "raw_key_forbidden_in_limited_prod"
    return True, None


def max_value_for_phase(cfg: ProductionGateConfig) -> int | None:
    if cfg.phase == OperationalPhase.CANARY:
        return cfg.canary_max_value_wei
    if cfg.phase == OperationalPhase.LIMITED:
        return cfg.limited_max_value_wei
    return None


def quorum_values(
    urls: tuple[str, ...],
    *,
    min_agree: int,
    fetcher: Callable[[str], int],
    timeout: float,
) -> tuple[int | None, dict[str, Any]]:
    """Return value when >= min_agree endpoints agree; else None."""
    counts: dict[int, int] = {}
    readings: dict[str, int] = {}
    errors: dict[str, str] = {}
    for url in urls:
        try:
            val = fetcher(url)
            readings[url] = val
            counts[val] = counts.get(val, 0) + 1
        except (RpcFetchError, OSError, TimeoutError) as exc:
            errors[url] = str(exc)

    quorum_val: int | None = None
    for val, cnt in counts.items():
        if cnt >= min_agree:
            quorum_val = val
            break

    detail = {
        "readings": readings,
        "errors": errors,
        "min_agree": min_agree,
        "quorum_met": quorum_val is not None,
        "quorum_value": quorum_val,
    }
    return quorum_val, detail


def _quorum_needed(cfg: ProductionGateConfig) -> int:
    """Fail-closed: outside lab never degrade below 2; insufficient URLs → unreachable quorum."""
    if cfg.phase == OperationalPhase.LAB:
        return min(cfg.quorum_min_agree, max(1, len(cfg.quorum_urls)))
    needed = max(2, cfg.quorum_min_agree)
    if len(cfg.quorum_urls) < needed:
        return needed  # quorum_values will fail (not enough agreeing readings)
    return needed


def quorum_balance(cfg: ProductionGateConfig, address: str) -> tuple[int | None, dict[str, Any]]:
    return quorum_values(
        cfg.quorum_urls,
        min_agree=_quorum_needed(cfg),
        fetcher=lambda url: fetch_balance(url, address, timeout=cfg.rpc_timeout_sec),
        timeout=cfg.rpc_timeout_sec,
    )


def quorum_nonce(cfg: ProductionGateConfig, address: str) -> tuple[int | None, dict[str, Any]]:
    return quorum_values(
        cfg.quorum_urls,
        min_agree=_quorum_needed(cfg),
        fetcher=lambda url: fetch_nonce(url, address, timeout=cfg.rpc_timeout_sec),
        timeout=cfg.rpc_timeout_sec,
    )


def post_sign_recheck(
    cfg: ProductionGateConfig,
    *,
    address: str,
    expected_nonce: int,
    balance_before_wei: int,
    intent_hash: str,
) -> tuple[bool, dict[str, Any]]:
    """After sign, before broadcast — verify balance+nonce still match intent."""
    bal, bal_detail = quorum_balance(cfg, address)
    nonce, nonce_detail = quorum_nonce(cfg, address)

    detail: dict[str, Any] = {
        "ts": utc_now(),
        "type": "post_sign_recheck",
        "intent_hash": intent_hash,
        "expected_nonce": expected_nonce,
        "balance_before_wei": balance_before_wei,
        "balance_quorum": bal_detail,
        "nonce_quorum": nonce_detail,
    }

    if bal is None or nonce is None:
        detail.update(
            {
                "allowed": False,
                "outcome": "quorum_unavailable",
                "severity": "critical",
                "action": "drop_tx",
                "message": "Quorum RPC failed — drop signed tx (fail closed)",
            }
        )
        append_alert(detail)
        return False, detail

    drift = False
    reasons: list[str] = []
    if nonce != expected_nonce:
        drift = True
        reasons.append("nonce_drift")
    if bal < balance_before_wei:
        drift = True
        reasons.append("balance_drift")

    detail.update(
        {
            "quorum_balance_wei": bal,
            "quorum_nonce": nonce,
            "allowed": not drift,
            "outcome": "verified" if not drift else "drift_detected",
            "drift_reasons": reasons,
        }
    )

    if drift:
        detail.update(
            {
                "severity": "critical",
                "action": "drop_tx",
                "message": "Post-sign drift — drop tx and alert on-call",
            }
        )
        append_alert(detail)

    return not drift, detail


def broadcast_raw_tx(rpc_url: str, raw_hex: str, *, timeout: float = 10.0) -> str:
    raw = raw_hex if raw_hex.startswith("0x") else f"0x{raw_hex}"
    return rpc_call(rpc_url, "eth_sendRawTransaction", [raw], timeout=timeout)
