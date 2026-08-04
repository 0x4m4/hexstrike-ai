#!/usr/bin/env python3
"""Defensive test: simulate attacker returning fake low balance on proxy RPC."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

SANDBOX = Path(__file__).resolve().parent
sys.path.insert(0, str(SANDBOX))

os.environ.setdefault("BOT_ADDRESS", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
os.environ.setdefault("RPC_URL", "http://127.0.0.1:8546")
os.environ.setdefault("DIRECT_RPC_URL", "http://127.0.0.1:8545")
os.environ.setdefault("MAX_BALANCE_DELTA_WEI", "0")

from balance_guard import GuardConfig, GuardState, evaluate_poll, pre_sign_verify

THRESHOLD = 500000000000000000  # 0.5 ETH
REAL_BALANCE = 10_000_000_000_000_000_000_000  # 10000 ETH (Anvil default)
FAKE_BALANCE = 0  # attacker returns 0x0


def simulate_attacker_proxy() -> None:
    cfg = GuardConfig.from_env()
    state = GuardState()

    def fake_fetch(url: str, address: str, timeout: float = 10.0) -> int:
        if url == cfg.primary_rpc:
            return FAKE_BALANCE  # attacker tampered proxy response
        return REAL_BALANCE  # direct Anvil still truthful

    with patch("balance_guard.fetch_balance", side_effect=fake_fetch), patch(
        "balance_guard.fetch_nonce", return_value=0
    ):
        checks = evaluate_poll(cfg, state)

    print("=== Attacker simulation: proxy says 0 ETH, direct says 10000 ETH ===")
    print(f"primary_wei (attacker): {checks['primary_wei']}")
    print(f"direct_wei   (truth)  : {checks['direct_wei']}")
    print(f"block_signing         : {checks['block_signing']}")
    print(f"block_reason          : {checks['block_reason']}")

    assert checks["block_signing"] is True
    assert checks["block_reason"] == "rpc_mismatch"
    print("✅ evaluate_poll BLOCKED tampered balance")

    with patch("balance_guard.fetch_balance", side_effect=fake_fetch):
        allowed, detail = pre_sign_verify(cfg, THRESHOLD)

    print(f"pre_sign allowed      : {allowed}")
    print(f"pre_sign outcome      : {detail.get('outcome')}")
    assert allowed is False
    print("✅ pre_sign_verify BLOCKED fake trigger")

    print("\nRESULT: hardened bot would NOT sign — attack failed.")


if __name__ == "__main__":
    simulate_attacker_proxy()
