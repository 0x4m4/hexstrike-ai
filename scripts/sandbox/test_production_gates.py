#!/usr/bin/env python3
"""Unit tests for Phase 0 production gates (GO-LIVE merge gate)."""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from unittest.mock import patch

SANDBOX = Path(__file__).resolve().parent
sys.path.insert(0, str(SANDBOX))

os.environ.setdefault("BOT_ADDRESS", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")

from production_gates import (  # noqa: E402
    IntentRegistry,
    NonceLock,
    OperationalPhase,
    ProductionGateConfig,
    SignerBackend,
    TxRateLimiter,
    check_allowlist,
    check_signer_policy,
    compute_intent_hash,
    post_sign_recheck,
    quorum_balance,
)

SAFE = "0x730ea0231808f42a20f8921ba7fbc788226768f5"
ATTACKER = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"


def _cfg(**overrides: object) -> ProductionGateConfig:
    base: dict[str, object] = dict(
        phase=OperationalPhase.LAB,
        allowed_funders=frozenset(),
        allowed_destinations=frozenset(),
        quorum_urls=("http://127.0.0.1:8545",),
        quorum_min_agree=1,
        kill_switch=False,
        max_rescues_per_window=10,
        rescue_window_sec=3600.0,
        cooldown_after_block_sec=1.0,
        canary_max_value_wei=10**15,
        limited_max_value_wei=10**16,
        signer_backend=SignerBackend.LOCAL_KEY,
        require_kms_outside_lab=False,
        require_allowlist=False,
        rpc_timeout_sec=5.0,
    )
    base.update(overrides)
    return ProductionGateConfig(**base)  # type: ignore[arg-type]


def test_intent_hash_stable() -> None:
    h1 = compute_intent_hash(to="0xABC", value_wei=1000, chain_id=56, nonce=3)
    h2 = compute_intent_hash(to="0xabc", value_wei=1000, chain_id=56, nonce=3)
    assert h1 == h2
    h3 = compute_intent_hash(to="0xabc", value_wei=1001, chain_id=56, nonce=3)
    assert h1 != h3
    h4 = compute_intent_hash(
        to="0xabc", value_wei=1000, chain_id=56, nonce=3, policy_version="v2"
    )
    assert h1 != h4
    print("PASS intent_hash")


def test_attack_06_allowlist_blocks_compromised_funder() -> None:
    cfg = _cfg(
        allowed_funders=frozenset({SAFE}),
        allowed_destinations=frozenset({SAFE}),
    )
    ok, reason = check_allowlist(cfg, funder=SAFE, destination=ATTACKER)
    assert not ok
    assert reason == "BLOCK_COMPROMISED_FUNDER"
    print("PASS attack_06_allowlist")


def test_attack_06_bypass_empty_allowlist_fail_closed() -> None:
    """Empty allowlist must not open the path when require_allowlist=True."""
    cfg = _cfg(phase=OperationalPhase.CANARY, require_allowlist=True)
    ok, reason = check_allowlist(cfg, funder=ATTACKER, destination=ATTACKER)
    assert not ok
    assert reason == "BLOCK_COMPROMISED_FUNDER"
    print("PASS attack_06_empty_bypass")


def test_attack_06_bypass_case_normalized() -> None:
    cfg = _cfg(
        allowed_funders=frozenset({SAFE}),
        allowed_destinations=frozenset({SAFE}),
    )
    # Mixed-case attacker still blocked
    ok, reason = check_allowlist(
        cfg,
        funder=SAFE,
        destination="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    )
    assert not ok
    assert reason == "BLOCK_COMPROMISED_FUNDER"
    print("PASS attack_06_case_bypass")


def test_attack_06_bypass_funder_only_mismatch() -> None:
    """Allowlisted destination but non-allowlisted funder must block."""
    cfg = _cfg(
        allowed_funders=frozenset({SAFE}),
        allowed_destinations=frozenset({SAFE, ATTACKER}),
    )
    ok, reason = check_allowlist(cfg, funder=ATTACKER, destination=ATTACKER)
    assert not ok
    assert reason == "BLOCK_COMPROMISED_FUNDER"
    print("PASS attack_06_funder_mismatch")


def test_attack_06_allowlisted_pair_passes() -> None:
    cfg = _cfg(
        allowed_funders=frozenset({SAFE}),
        allowed_destinations=frozenset({SAFE}),
        require_allowlist=True,
    )
    ok, reason = check_allowlist(cfg, funder=SAFE, destination=SAFE)
    assert ok
    assert reason is None
    print("PASS attack_06_allow_pass")


def test_dedup_intent_nonce() -> None:
    reg = IntentRegistry()
    ih = compute_intent_hash(to="0xabc", value_wei=1, chain_id=31337, nonce=1)
    assert reg.claim(ih, 1)
    assert not reg.claim(ih, 1)
    reg.release(ih, 1)
    assert reg.claim(ih, 1)
    print("PASS dedup")


def test_nonce_lock_single_flight() -> None:
    lock = NonceLock.for_address("0xabc")
    acquired = []

    def worker() -> None:
        if lock.acquire(blocking=False):
            acquired.append(threading.current_thread().name)
            lock.release()

    threads = [threading.Thread(target=worker, name=f"t{i}") for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(acquired) >= 1
    print("PASS nonce_lock")


def test_post_sign_recheck_blocks_nonce_drift() -> None:
    cfg = _cfg(quorum_urls=("http://a", "http://b", "http://c"), quorum_min_agree=2)
    addr = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    def fake_balance(url: str, address: str, timeout: float = 10.0) -> int:
        return 300_000_000_000_000_000

    def fake_nonce(url: str, address: str, timeout: float = 10.0) -> int:
        return 5 if "c" in url else 6

    with patch("production_gates.fetch_balance", side_effect=fake_balance), patch(
        "production_gates.fetch_nonce", side_effect=fake_nonce
    ):
        ok, detail = post_sign_recheck(
            cfg,
            address=addr,
            expected_nonce=5,
            balance_before_wei=300_000_000_000_000_000,
            intent_hash="abc123",
        )
    assert not ok
    assert detail["outcome"] == "drift_detected"
    assert "nonce_drift" in detail["drift_reasons"]
    print("PASS post_sign_recheck")


def test_quorum_balance_2_of_3() -> None:
    cfg = _cfg(quorum_urls=("http://a", "http://b", "http://c"), quorum_min_agree=2)

    def fake_balance(url: str, address: str, timeout: float = 10.0) -> int:
        if url == "http://c":
            return 999
        return 100

    with patch("production_gates.fetch_balance", side_effect=fake_balance):
        val, detail = quorum_balance(cfg, "0xabc")
    assert val == 100
    assert detail["quorum_met"]
    print("PASS quorum_2_of_3")


def test_shadow_mode_blocks_sign() -> None:
    cfg = _cfg(
        phase=OperationalPhase.SHADOW,
        allowed_funders=frozenset({"0xabc"}),
        allowed_destinations=frozenset({"0xabc"}),
        signer_backend=SignerBackend.KMS,
        require_kms_outside_lab=True,
        require_allowlist=True,
    )
    ok, reason = check_signer_policy(cfg)
    assert not ok
    assert reason == "shadow_mode_no_sign"
    print("PASS shadow_mode")


def test_rate_limiter() -> None:
    cfg = _cfg(max_rescues_per_window=2, cooldown_after_block_sec=60.0, quorum_urls=())
    limiter = TxRateLimiter(cfg)
    assert limiter.check()[0]
    limiter.record_attempt()
    assert limiter.check()[0]
    limiter.record_attempt()
    ok, reason = limiter.check()
    assert not ok
    assert reason == "rate_limit_exceeded"
    print("PASS rate_limiter")


def main() -> int:
    tests = [
        test_intent_hash_stable,
        test_attack_06_allowlist_blocks_compromised_funder,
        test_attack_06_bypass_empty_allowlist_fail_closed,
        test_attack_06_bypass_case_normalized,
        test_attack_06_bypass_funder_only_mismatch,
        test_attack_06_allowlisted_pair_passes,
        test_dedup_intent_nonce,
        test_nonce_lock_single_flight,
        test_post_sign_recheck_blocks_nonce_drift,
        test_quorum_balance_2_of_3,
        test_shadow_mode_blocks_sign,
        test_rate_limiter,
    ]
    for fn in tests:
        fn()
    print("\nRESULT: all production gate tests PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
