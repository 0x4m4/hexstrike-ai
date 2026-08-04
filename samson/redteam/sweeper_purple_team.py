"""Two-sided purple-team sweeper module (attack + defense).

Attack (synthetic, Anvil/Hardhat ONLY):
  Emulates the BNB-sweeper pattern — watch wallet balance, when
  ``balance >= min_sweep`` drain full balance to a destination wallet.
  Mainnet / BSC production chains are hard-refused.

Defense:
  Detect full-balance auto-drain indicators, mark destination as
  ``is_risk`` in ``web3_recon_artifacts`` so guardrail blocks outbound.

This is authorized purple-team tooling — not a live mainnet sweeper.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

from eth_account import Account

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ConfigurationError
from samson.core.scope import ScopeEnforcer
from samson.redteam.schemas import (
    SweeperAttackResult,
    SweeperDefenseResult,
    SweeperPurpleTeamResult,
)
from samson.redteam.validation_node import LocalBlockchainSandbox

logger = logging.getLogger(__name__)

_TRANSFER_GAS = 21_000
_DEFAULT_MIN_SWEEP_WEI = 10**15  # 0.001 ETH synthetic threshold
_DEFAULT_FUND_WEI = 10**18

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SyntheticSweeperAttacker:
    """Anvil-only sweeper attack emulating japancode/BNB-Sweeper-Bot rules."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._sandbox = LocalBlockchainSandbox(self._settings)

    async def close(self) -> None:
        await self._sandbox.close()

    async def execute(
        self,
        *,
        operator_id: str = "operator-alpha",
        request_id: UUID | None = None,
        run_id: UUID | None = None,
        watched_private_key: str | None = None,
        destination_wallet: str | None = None,
        min_sweep_wei: int | None = None,
        fund_wei: int | None = None,
        gas_gwei: int | None = None,
    ) -> SweeperAttackResult:
        """Fund watched wallet → trigger threshold → full-balance sweep on Anvil."""
        request_id = request_id or uuid4()
        execution_id = uuid4()
        key = self._normalize_key(
            watched_private_key
            if watched_private_key is not None
            else (
                self._settings.web3_private_key
                or os.environ.get("SAMSON_WEB3_PRIVATE_KEY")
                or os.environ.get("WEB3_PRIVATE_KEY")
                or ""
            )
        )
        dest = (
            destination_wallet
            or self._settings.web3_diversion_to
            or "0x000000000000000000000000000000000000dEaD"
        )
        threshold = int(min_sweep_wei if min_sweep_wei is not None else _DEFAULT_MIN_SWEEP_WEI)
        seed = int(fund_wei if fund_wei is not None else _DEFAULT_FUND_WEI)

        try:
            await self._sandbox.connect()
            w3 = self._sandbox._w3_or_raise()  # noqa: SLF001
            chain_id = int(await w3.eth.chain_id)
            self._sandbox._assert_safe_chain(chain_id)  # noqa: SLF001

            account = Account.from_key(key)
            watched = w3.to_checksum_address(account.address)
            destination = w3.to_checksum_address(dest)
            if watched.lower() == destination.lower():
                raise ConfigurationError(
                    "Sweeper destination must differ from watched wallet",
                    watched=watched,
                    destination=destination,
                )

            # Seed balance above threshold (Anvil cheatcode).
            await self._sandbox._rpc_set_balance(watched, seed)  # noqa: SLF001
            balance_before = int(await w3.eth.get_balance(watched))
            triggered = balance_before >= threshold

            if not triggered:
                return SweeperAttackResult(
                    execution_id=execution_id,
                    request_id=request_id,
                    watched_wallet=watched,
                    destination_wallet=destination,
                    triggered=False,
                    swept=False,
                    balance_before_wei=balance_before,
                    balance_after_wei=balance_before,
                    min_sweep_wei=threshold,
                    chain_id=chain_id,
                    rpc_url=self._sandbox._rpc_url,  # noqa: SLF001
                    error="balance_below_min_sweep — sweeper idle",
                )

            # Race-style gas (higher gwei = faster inclusion — pattern signal for defense).
            network_gas = int(await w3.eth.gas_price)
            if gas_gwei is not None:
                gas_price = int(gas_gwei) * 10**9
            else:
                gas_price = max(network_gas * 2, network_gas + 10**9)

            fee = gas_price * _TRANSFER_GAS
            if balance_before <= fee:
                await self._sandbox._rpc_set_balance(watched, fee + seed)  # noqa: SLF001
                balance_before = int(await w3.eth.get_balance(watched))
            value = balance_before - fee
            if value <= 0:
                raise ConfigurationError(
                    "Insufficient balance after gas for synthetic sweep",
                    balance_before=balance_before,
                    fee=fee,
                )

            nonce = int(await w3.eth.get_transaction_count(watched, "pending"))
            tx = {
                "nonce": nonce,
                "to": destination,
                "value": value,
                "gas": _TRANSFER_GAS,
                "gasPrice": gas_price,
                "chainId": chain_id,
                "data": b"",
            }
            signed = account.sign_transaction(tx)
            raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
            if raw is None:
                raise RuntimeError("eth_account did not return raw transaction bytes")

            tx_hash = await w3.eth.send_raw_transaction(raw)
            receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            tx_hash_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
            if not tx_hash_hex.startswith("0x"):
                tx_hash_hex = "0x" + tx_hash_hex

            balance_after = int(await w3.eth.get_balance(watched))
            swept = balance_after == 0 and int(receipt.get("status", 0)) == 1
            swept_wei = max(balance_before - balance_after, 0)

            result = SweeperAttackResult(
                execution_id=execution_id,
                request_id=request_id,
                watched_wallet=watched,
                destination_wallet=destination,
                triggered=True,
                swept=swept,
                balance_before_wei=balance_before,
                balance_after_wei=balance_after,
                swept_wei=swept_wei,
                min_sweep_wei=threshold,
                gas_price_wei=gas_price,
                tx_hash=tx_hash_hex,
                chain_id=chain_id,
                rpc_url=self._sandbox._rpc_url,  # noqa: SLF001
                error=None if swept else "sweep_incomplete_balance_remaining",
            )
            logger.warning(
                "SWEEPER ATTACK (synthetic) watched=%s dest=%s swept=%s wei=%s tx=%s",
                watched,
                destination,
                swept,
                swept_wei,
                tx_hash_hex,
            )
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error("Synthetic sweeper attack failed: %s", exc)
            return SweeperAttackResult(
                execution_id=execution_id,
                request_id=request_id,
                watched_wallet="unknown",
                destination_wallet=dest,
                triggered=False,
                swept=False,
                min_sweep_wei=threshold,
                rpc_url=str(self._settings.web3_rpc_url),
                error=f"{type(exc).__name__}: {exc}",
            )

    @staticmethod
    def _normalize_key(private_key: str) -> str:
        key = (private_key or "").strip()
        if not key:
            raise ConfigurationError(
                "Watched wallet private key missing — set SAMSON_WEB3_PRIVATE_KEY"
            )
        if not key.startswith("0x"):
            key = "0x" + key
        return key


class SweeperDefenseDetector:
    """Detect sweeper patterns and load destination into guardrail risk list."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)

    def analyze(
        self,
        attack: SweeperAttackResult,
        *,
        operator_id: str = "operator-alpha",
        run_id: UUID | None = None,
    ) -> SweeperDefenseResult:
        """Score attack telemetry → indicators → persist destination as high-risk."""
        detection_id = uuid4()
        indicators: list[str] = []

        if attack.triggered and attack.swept:
            indicators.append("full_balance_drain")
            indicators.append("auto_transfer_on_threshold")
        if (
            attack.watched_wallet
            and attack.destination_wallet
            and attack.watched_wallet.lower() != attack.destination_wallet.lower()
        ):
            indicators.append("destination_not_watched_wallet")
        if attack.gas_price_wei and attack.chain_id in {31337, 1337}:
            # Elevated gas vs base Anvil 1 gwei signals race-style sweeper.
            if attack.gas_price_wei >= 2 * 10**9:
                indicators.append("high_priority_gas_race")
        if attack.pattern_id:
            indicators.append("sweeper_pattern_bnb_style")
        if attack.swept_wei > 0 and attack.balance_after_wei == 0:
            indicators.append("watched_wallet_zeroed")

        detected = bool(attack.swept) and len(indicators) >= 3
        risk_level = "high" if detected else ("medium" if indicators else "low")
        blocked = False
        persisted = False

        if detected and attack.destination_wallet:
            persisted = self._persist_risk_destination(
                attack.destination_wallet,
                operator_id=operator_id,
                run_id=run_id,
                request_id=attack.request_id,
                indicators=indicators,
                attack=attack,
            )
            blocked = persisted

        remediation = [
            "Block destination wallet in guardrail outbound proxy (web3_recon is_risk)",
            "Rotate watched-wallet keys; assume sweeper listener compromise",
            "Alert on full-balance transfers with elevated gas from monitored hot wallets",
            "Require human approval for native transfers above threshold",
        ]

        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=attack.request_id,
                tool="sweeper_defense",
                operator_id=operator_id,
                action="analyze_sweeper_attack",
                outcome="pass" if detected else "hold",
                payload_hash=sha256_payload(
                    {
                        "detected": detected,
                        "destination": attack.destination_wallet,
                        "indicators": indicators,
                    }
                ),
                duration_ms=0,
                run_id=run_id,
            )

        logger.warning(
            "SWEEPER DEFENSE detected=%s blocked=%s dest=%s indicators=%s",
            detected,
            blocked,
            attack.destination_wallet,
            ",".join(indicators),
        )
        return SweeperDefenseResult(
            detection_id=detection_id,
            request_id=attack.request_id,
            detected=detected,
            blocked=blocked,
            risk_level=risk_level,
            destination_wallet=attack.destination_wallet,
            watched_wallet=attack.watched_wallet,
            indicators=indicators,
            guardrail_loaded=blocked,
            persisted_web3_recon=persisted,
            remediation=remediation,
        )

    def _persist_risk_destination(
        self,
        destination: str,
        *,
        operator_id: str,
        run_id: UUID | None,
        request_id: UUID,
        indicators: list[str],
        attack: SweeperAttackResult,
    ) -> bool:
        artifact_id = uuid4()
        payload = {
            "source": "sweeper_purple_team",
            "pattern_id": attack.pattern_id,
            "indicators": indicators,
            "attack_tx_hash": attack.tx_hash,
            "watched_wallet": attack.watched_wallet,
            "swept_wei": attack.swept_wei,
            "synthetic": True,
        }
        try:
            self._db.execute(
                """
                INSERT INTO web3_recon_artifacts (
                    artifact_id, request_id, run_id, operator_id, address,
                    risk_level, is_risk, entity_name, entity_id, entity_type,
                    label_name, chains_seen, labels, from_cache, raw_payload,
                    rag_doc_path, collected_at
                ) VALUES (
                    :artifact_id, :request_id, :run_id, :operator_id, :address,
                    'high', TRUE, 'SweeperDestination', 'sweeper-dest', 'theft',
                    'Synthetic Sweeper Drain Target', :chains, :labels, FALSE,
                    CAST(:raw_payload AS jsonb), NULL, :collected_at
                )
                ON CONFLICT (artifact_id) DO NOTHING
                """,
                {
                    "artifact_id": str(artifact_id),
                    "request_id": str(request_id),
                    "run_id": str(run_id) if run_id else None,
                    "operator_id": operator_id,
                    "address": destination,
                    "chains": ["anvil_local"] if attack.chain_id in {31337, 1337} else [],
                    "labels": ["sweeper", "drain_destination", "purple_team"],
                    "raw_payload": json.dumps(payload, ensure_ascii=False),
                    "collected_at": _utcnow().isoformat(),
                },
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to persist sweeper destination risk: %s", exc)
            return False


class SweeperPurpleTeam:
    """Orchestrate synthetic sweeper attack → defense detection → assert."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._attacker = SyntheticSweeperAttacker(self._settings)
        self._defender = SweeperDefenseDetector(self._settings)
        self._db = Database(self._settings)
        self._scope = ScopeEnforcer(self._settings)

    async def close(self) -> None:
        await self._attacker.close()

    async def run(
        self,
        *,
        operator_id: str = "operator-alpha",
        request_id: UUID | None = None,
        run_id: UUID | None = None,
        destination_wallet: str | None = None,
        min_sweep_wei: int | None = None,
        fund_wei: int | None = None,
        gas_gwei: int | None = None,
    ) -> SweeperPurpleTeamResult:
        request_id = request_id or uuid4()
        self._scope.assert_operator(operator_id, request_id=request_id)

        attack = await self._attacker.execute(
            operator_id=operator_id,
            request_id=request_id,
            run_id=run_id,
            destination_wallet=destination_wallet,
            min_sweep_wei=min_sweep_wei,
            fund_wei=fund_wei,
            gas_gwei=gas_gwei,
        )
        defense = self._defender.analyze(
            attack,
            operator_id=operator_id,
            run_id=run_id,
        )
        # Assertion: successful synthetic sweep must be detected AND destination blocked.
        assertion_passed = (
            (not attack.swept and not defense.detected)
            or (attack.swept and defense.detected and defense.blocked)
        )
        result = SweeperPurpleTeamResult(
            request_id=request_id,
            operator_id=operator_id,
            attack=attack,
            defense=defense,
            assertion_passed=assertion_passed,
        )
        await asyncio.to_thread(self._persist_run, result, run_id=run_id)
        return result

    def _persist_run(
        self,
        result: SweeperPurpleTeamResult,
        *,
        run_id: UUID | None,
    ) -> None:
        self._db.execute(
            """
            INSERT INTO sweeper_purple_team_runs (
                run_artifact_id, request_id, exercise_run_id, operator_id,
                watched_wallet, destination_wallet, attack_triggered, attack_swept,
                attack_tx_hash, swept_wei, defense_detected, defense_blocked,
                risk_level, indicators, assertion_passed, raw_payload
            ) VALUES (
                :run_artifact_id, :request_id, :exercise_run_id, :operator_id,
                :watched_wallet, :destination_wallet, :attack_triggered, :attack_swept,
                :attack_tx_hash, :swept_wei, :defense_detected, :defense_blocked,
                :risk_level, :indicators, :assertion_passed, CAST(:raw_payload AS jsonb)
            )
            """,
            {
                "run_artifact_id": str(uuid4()),
                "request_id": str(result.request_id),
                "exercise_run_id": str(run_id) if run_id else None,
                "operator_id": result.operator_id,
                "watched_wallet": result.attack.watched_wallet,
                "destination_wallet": result.attack.destination_wallet,
                "attack_triggered": result.attack.triggered,
                "attack_swept": result.attack.swept,
                "attack_tx_hash": result.attack.tx_hash,
                "swept_wei": result.attack.swept_wei,
                "defense_detected": result.defense.detected,
                "defense_blocked": result.defense.blocked,
                "risk_level": result.defense.risk_level,
                "indicators": result.defense.indicators,
                "assertion_passed": result.assertion_passed,
                "raw_payload": result.model_dump_json(),
            },
        )
