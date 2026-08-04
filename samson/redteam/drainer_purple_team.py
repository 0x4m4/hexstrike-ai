"""Multi-family purple-team drainer lab (Anvil attack + defense IOC).

Threat models (synthetic / defense only — NOT live malware):
  - emmarktech/evm-drainer       → family ``evm_erc20``
  - emmarktech/apeterminal-main  → family ``usdt_evm``
  - meirekuma46/TRX-Drainer      → family ``trx_trc20`` (defense IOC catalog)

Policy:
  - EVM/USDT attack paths run ONLY on local Anvil/Hardhat (chain 31337/1337).
  - TRX path never sends TRON mainnet/Nile/Shasta drain transactions.
  - No cloning or execution of public drain-bot malware against real wallets.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence
from uuid import UUID, uuid4

from eth_account import Account
from web3 import AsyncWeb3

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ConfigurationError
from samson.core.scope import ScopeEnforcer
from samson.redteam.schemas import DrainerFamilyResult, DrainerPurpleTeamResult
from samson.redteam.validation_node import LocalBlockchainSandbox

logger = logging.getLogger(__name__)

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "MockERC20.json"
# Anvil account #1 — synthetic victim (public test key, never mainnet).
_ANVIL_VICTIM_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
_DEFAULT_TOKEN_AMOUNT = 1_000_000_000
_FAMILY = Literal["evm_erc20", "usdt_evm", "trx_trc20"]

_SOURCE_REPOS: dict[str, str] = {
    "evm_erc20": "emmarktech/evm-drainer",
    "usdt_evm": "emmarktech/apeterminal-main",
    "trx_trc20": "meirekuma46/TRX-Drainer",
}

TRX_DRAINER_IOCS: tuple[str, ...] = (
    "energy_rental_plus_unlimited_trc20_approve",
    "tronlink_trust_wallet_phishing_dapp",
    "multi_wallet_consolidation_sweeper",
    "hidden_energy_optimized_routing",
)

_TRX_REMEDIATION: tuple[str, ...] = (
    "Never approve unlimited TRC20 spenders from unknown dApps",
    "Revoke TRC20 allowances after any energy-rental or airdrop flow",
    "Block sink addresses labeled trx_drainer_ioc in outbound guardrail",
    "Alert on TriggerSmartContract approve(max) to new spenders",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _tx_hex(value: Any) -> str:
    if hasattr(value, "to_0x_hex"):
        return value.to_0x_hex()
    text = value.hex() if hasattr(value, "hex") else str(value)
    return text if text.startswith("0x") else f"0x{text}"


class MultiDrainerPurpleTeam:
    """Synthetic attack + defense for EVM ERC-20, USDT-EVM, and TRX IOC families."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._sandbox = LocalBlockchainSandbox(self._settings)
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._scope = ScopeEnforcer(self._settings)
        self._artifact = json.loads(_FIXTURE.read_text(encoding="utf-8"))

    async def close(self) -> None:
        await self._sandbox.close()

    async def run(
        self,
        *,
        operator_id: str = "operator-alpha",
        request_id: UUID | None = None,
        run_id: UUID | None = None,
        families: Sequence[str] | None = None,
        token_amount: int = _DEFAULT_TOKEN_AMOUNT,
    ) -> DrainerPurpleTeamResult:
        request_id = request_id or uuid4()
        self._scope.assert_operator(operator_id, request_id=request_id)
        selected = tuple(families or ("evm_erc20", "usdt_evm", "trx_trc20"))
        results: list[DrainerFamilyResult] = []

        needs_sandbox = any(f in ("evm_erc20", "usdt_evm") for f in selected)
        try:
            if needs_sandbox:
                await self._sandbox.connect()
            for family in selected:
                if family in ("evm_erc20", "usdt_evm"):
                    results.append(
                        await self._run_evm_family(
                            family=family,  # type: ignore[arg-type]
                            request_id=request_id,
                            operator_id=operator_id,
                            run_id=run_id,
                            token_amount=token_amount,
                        )
                    )
                elif family == "trx_trc20":
                    results.append(
                        await asyncio.to_thread(
                            self._run_trx_defense,
                            request_id=request_id,
                            operator_id=operator_id,
                            run_id=run_id,
                        )
                    )
                else:
                    raise ConfigurationError(f"Unknown drainer family: {family}")
        finally:
            if needs_sandbox:
                await self._sandbox.close()

        assertion_passed = all(
            (item.attack_success and item.defense_blocked)
            if item.family in ("evm_erc20", "usdt_evm")
            else item.defense_blocked
            for item in results
        )
        # Empty selection would vacuously pass — refuse.
        if not results:
            assertion_passed = False

        result = DrainerPurpleTeamResult(
            request_id=request_id,
            operator_id=operator_id,
            families_run=list(selected),
            results=results,
            assertion_passed=assertion_passed,
        )
        await asyncio.to_thread(self._persist_suite, result, run_id=run_id)
        return result

    async def _run_evm_family(
        self,
        *,
        family: _FAMILY,
        request_id: UUID,
        operator_id: str,
        run_id: UUID | None,
        token_amount: int,
    ) -> DrainerFamilyResult:
        if family == "usdt_evm":
            token_name, token_symbol, decimals = "Mock USDT", "USDT", 6
        else:
            token_name, token_symbol, decimals = "Mock ERC20", "MOCK", 18

        source = _SOURCE_REPOS[family]
        indicators: list[str] = []
        remediation = [
            "Revoke unlimited ERC-20 allowances; prefer exact approve amounts",
            "Block drain-sink addresses marked is_risk in web3_recon_artifacts",
            "Alert on approve(max) followed by transferFrom from hot wallets",
            "Require human approval for first-time token spenders",
        ]

        try:
            deployer_key = self._normalize_key(
                self._settings.web3_private_key
                or os.environ.get("SAMSON_WEB3_PRIVATE_KEY")
                or os.environ.get("WEB3_PRIVATE_KEY")
                or ""
            )
            victim_key = self._normalize_key(_ANVIL_VICTIM_KEY)
            deployer = Account.from_key(deployer_key)
            victim = Account.from_key(victim_key)

            if not self._sandbox.connected:
                await self._sandbox.connect()
            w3 = self._sandbox._w3_or_raise()  # noqa: SLF001
            chain_id = int(await w3.eth.chain_id)
            self._sandbox._assert_safe_chain(chain_id)  # noqa: SLF001
            if chain_id not in {31337, 1337}:
                raise ConfigurationError(
                    f"Drainer purple-team refuses non-local chain_id={chain_id}"
                )

            destination = w3.to_checksum_address(deployer.address)
            victim_addr = w3.to_checksum_address(victim.address)
            deployer_addr = w3.to_checksum_address(deployer.address)

            # Ensure victim has gas for approve.
            await self._sandbox._rpc_set_balance(victim_addr, 10**18)  # noqa: SLF001

            token_addr = await self._deploy_mock_erc20(
                w3,
                account=deployer,
                from_addr=deployer_addr,
                chain_id=chain_id,
                name=token_name,
                symbol=token_symbol,
                decimals=decimals,
            )
            token = w3.eth.contract(address=token_addr, abi=self._artifact["abi"])

            await self._send_contract_tx(
                w3,
                account=deployer,
                from_addr=deployer_addr,
                chain_id=chain_id,
                fn=token.functions.mint(victim_addr, int(token_amount)),
            )
            bal = int(await token.functions.balanceOf(victim_addr).call())
            indicators.append("token_minted_to_victim")

            approve_tx = await self._send_contract_tx(
                w3,
                account=victim,
                from_addr=victim_addr,
                chain_id=chain_id,
                fn=token.functions.approve(destination, 2**256 - 1),
            )
            indicators.append("unlimited_erc20_approve")

            drain_tx = await self._send_contract_tx(
                w3,
                account=deployer,
                from_addr=deployer_addr,
                chain_id=chain_id,
                fn=token.functions.transferFrom(victim_addr, destination, bal),
            )
            dest_bal = int(await token.functions.balanceOf(destination).call())
            victim_bal = int(await token.functions.balanceOf(victim_addr).call())
            attack_success = dest_bal == bal and victim_bal == 0 and bal > 0
            if attack_success:
                indicators.extend(
                    [
                        "transferFrom_full_balance_drain",
                        "victim_token_balance_zeroed",
                        f"drainer_pattern_{family}",
                    ]
                )

            defense_detected = attack_success and len(indicators) >= 3
            persisted = False
            if defense_detected:
                persisted = await asyncio.to_thread(
                    self._persist_risk_destination,
                    destination=destination,
                    family=family,
                    request_id=request_id,
                    operator_id=operator_id,
                    run_id=run_id,
                    token_symbol=token_symbol,
                    token_address=token_addr,
                    approve_tx=approve_tx,
                    drain_tx=drain_tx,
                    amount_raw=bal,
                    indicators=indicators,
                )
            defense_blocked = persisted

            if self._settings.audit_enabled:
                self._audit.write_redteam_audit(
                    request_id=request_id,
                    tool="drainer_purple_team",
                    operator_id=operator_id,
                    action=f"family_{family}",
                    outcome="pass" if attack_success and defense_blocked else "hold",
                    payload_hash=sha256_payload(
                        {
                            "family": family,
                            "destination": destination,
                            "attack_success": attack_success,
                            "defense_blocked": defense_blocked,
                        }
                    ),
                    duration_ms=0,
                    run_id=run_id,
                )

            logger.warning(
                "DRAINER FAMILY %s attack=%s defense=%s dest=%s token=%s",
                family,
                attack_success,
                defense_blocked,
                destination,
                token_symbol,
            )
            return DrainerFamilyResult(
                family=family,
                source_repo=source,
                attack_executed=True,
                attack_success=attack_success,
                defense_detected=defense_detected,
                defense_blocked=defense_blocked,
                victim_wallet=victim_addr,
                destination_wallet=destination,
                token_address=token_addr,
                token_symbol=token_symbol,
                amount_raw=bal if attack_success else 0,
                approve_tx=approve_tx,
                drain_tx=drain_tx,
                indicators=indicators,
                remediation=remediation,
                error=None if attack_success else "drain_incomplete",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Drainer family %s failed", family)
            return DrainerFamilyResult(
                family=family,
                source_repo=source,
                attack_executed=False,
                attack_success=False,
                defense_detected=False,
                defense_blocked=False,
                token_symbol=token_symbol,
                indicators=indicators,
                remediation=remediation,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _run_trx_defense(
        self,
        *,
        request_id: UUID,
        operator_id: str,
        run_id: UUID | None,
    ) -> DrainerFamilyResult:
        """Defense-only TRX/TRC20 IOC catalog — no mainnet drain execution."""
        indicators = list(TRX_DRAINER_IOCS)
        # Synthetic TRON sink marker (not a valid EVM address) for guardrail drills.
        marker = "T" + ("9" * 33)
        persisted = self._persist_risk_destination(
            destination=marker,
            family="trx_trc20",
            request_id=request_id,
            operator_id=operator_id,
            run_id=run_id,
            token_symbol="TRC20",
            token_address=None,
            approve_tx=None,
            drain_tx=None,
            amount_raw=0,
            indicators=indicators,
            chains=["tron"],
            entity_name="TrxDrainerIocSink",
            entity_id="trx-drainer-ioc",
            label_name="TRX Drainer IOC Sink",
        )
        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=request_id,
                tool="drainer_purple_team",
                operator_id=operator_id,
                action="family_trx_trc20",
                outcome="pass" if persisted else "hold",
                payload_hash=sha256_payload(
                    {"family": "trx_trc20", "iocs": indicators, "persisted": persisted}
                ),
                duration_ms=0,
                run_id=run_id,
            )
        logger.warning(
            "DRAINER FAMILY trx_trc20 defense_ioc persisted=%s iocs=%s",
            persisted,
            len(indicators),
        )
        return DrainerFamilyResult(
            family="trx_trc20",
            source_repo=_SOURCE_REPOS["trx_trc20"],
            attack_executed=False,
            attack_success=False,
            defense_detected=True,
            defense_blocked=persisted,
            destination_wallet=marker,
            token_symbol="TRC20",
            indicators=indicators,
            remediation=list(_TRX_REMEDIATION),
            error=None if persisted else "trx_ioc_persist_failed",
        )

    async def _deploy_mock_erc20(
        self,
        w3: AsyncWeb3,
        *,
        account: Account,
        from_addr: str,
        chain_id: int,
        name: str,
        symbol: str,
        decimals: int,
    ) -> str:
        contract = w3.eth.contract(
            abi=self._artifact["abi"], bytecode=self._artifact["bytecode"]
        )
        nonce = int(await w3.eth.get_transaction_count(from_addr, "pending"))
        gas_price = int(await w3.eth.gas_price)
        tx = await contract.constructor(name, symbol, int(decimals)).build_transaction(
            {
                "from": from_addr,
                "nonce": nonce,
                "gas": 2_000_000,
                "gasPrice": gas_price,
                "chainId": chain_id,
            }
        )
        signed = account.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or getattr(
            signed, "rawTransaction", None
        )
        if raw is None:
            raise RuntimeError("eth_account did not return raw transaction bytes")
        tx_hash = await w3.eth.send_raw_transaction(raw)
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        address = receipt.get("contractAddress")
        if not address:
            raise ConfigurationError("MockERC20 deploy returned empty contractAddress")
        if int(receipt.get("status", 0)) != 1:
            raise ConfigurationError("MockERC20 deploy transaction failed")
        return w3.to_checksum_address(address)

    async def _send_contract_tx(
        self,
        w3: AsyncWeb3,
        *,
        account: Account,
        from_addr: str,
        chain_id: int,
        fn: Any,
    ) -> str:
        nonce = int(await w3.eth.get_transaction_count(from_addr, "pending"))
        gas_price = int(await w3.eth.gas_price)
        tx = await fn.build_transaction(
            {
                "from": from_addr,
                "nonce": nonce,
                "gas": 500_000,
                "gasPrice": gas_price,
                "chainId": chain_id,
            }
        )
        signed = account.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or getattr(
            signed, "rawTransaction", None
        )
        if raw is None:
            raise RuntimeError("eth_account did not return raw transaction bytes")
        tx_hash = await w3.eth.send_raw_transaction(raw)
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if int(receipt.get("status", 0)) != 1:
            raise ConfigurationError(f"Contract tx failed: {_tx_hex(tx_hash)}")
        return _tx_hex(tx_hash)

    def _persist_risk_destination(
        self,
        *,
        destination: str,
        family: str,
        request_id: UUID,
        operator_id: str,
        run_id: UUID | None,
        token_symbol: str,
        token_address: str | None,
        approve_tx: str | None,
        drain_tx: str | None,
        amount_raw: int,
        indicators: list[str],
        chains: list[str] | None = None,
        entity_name: str = "DrainerPurpleTeamSink",
        entity_id: str = "drainer-purple-sink",
        label_name: str = "Synthetic Drainer Drain Target",
    ) -> bool:
        artifact_id = uuid4()
        payload = {
            "source": "drainer_purple_team",
            "family": family,
            "source_repo": _SOURCE_REPOS.get(family),
            "indicators": indicators,
            "token_symbol": token_symbol,
            "token_address": token_address,
            "approve_tx": approve_tx,
            "drain_tx": drain_tx,
            "amount_raw": amount_raw,
            "synthetic": True,
            "sandbox_only": family != "trx_trc20",
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
                    'high', TRUE, :entity_name, :entity_id, 'theft',
                    :label_name, :chains, :labels, FALSE,
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
                    "entity_name": entity_name,
                    "entity_id": entity_id,
                    "label_name": label_name,
                    "chains": chains
                    if chains is not None
                    else ["anvil_local"],
                    "labels": ["drainer", family, "drain_destination", "purple_team"],
                    "raw_payload": json.dumps(payload, ensure_ascii=False),
                    "collected_at": _utcnow().isoformat(),
                },
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to persist drainer destination risk: %s", exc)
            return False

    def _persist_suite(
        self,
        result: DrainerPurpleTeamResult,
        *,
        run_id: UUID | None,
    ) -> None:
        self._db.execute(
            """
            INSERT INTO drainer_purple_team_runs (
                run_artifact_id, request_id, exercise_run_id, operator_id,
                families_run, assertion_passed, raw_payload
            ) VALUES (
                :run_artifact_id, :request_id, :exercise_run_id, :operator_id,
                :families_run, :assertion_passed, CAST(:raw_payload AS jsonb)
            )
            """,
            {
                "run_artifact_id": str(uuid4()),
                "request_id": str(result.request_id),
                "exercise_run_id": str(run_id) if run_id else None,
                "operator_id": result.operator_id,
                "families_run": result.families_run,
                "assertion_passed": result.assertion_passed,
                "raw_payload": result.model_dump_json(),
            },
        )

    @staticmethod
    def _normalize_key(private_key: str) -> str:
        key = (private_key or "").strip()
        if not key:
            raise ConfigurationError(
                "SAMSON_WEB3_PRIVATE_KEY missing — required for Anvil deployer"
            )
        if not key.startswith("0x"):
            key = "0x" + key
        return key
