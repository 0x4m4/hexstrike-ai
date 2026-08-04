"""Local blockchain exploitation sandbox for Samson SBM financial validation.

Connects exclusively to Anvil/Hardhat (Docker network or loopback). Refuses
Ethereum/BSC mainnet. Private keys are read from the environment / settings —
never hardcoded.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from eth_account import Account
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload, vector_literal
from samson.core.errors import ConfigurationError
from samson.core.http_client import OllamaClient
from samson.redteam.arkham_collector import SamsonArkhamClient
from samson.redteam.schemas import ArkhamIntelArtifact

logger = logging.getLogger(__name__)

# Local Anvil / Hardhat chain ids (gas is free; balance gate still fetches + persists).
_LOCAL_CHAIN_IDS = frozenset({31337, 1337})

# Allowed RPC hostnames for the local / Docker sandbox (no public mainnet RPCs).
_LOCAL_RPC_HOSTS = frozenset(
    {
        "127.0.0.1",
        "localhost",
        "::1",
        "host.docker.internal",
        "anvil",
        "hardhat",
        "samson-anvil",
        "foundry",
    }
)

# Hard-refuse production chain ids even if an operator mis-points the RPC URL.
_FORBIDDEN_CHAIN_IDS = frozenset(
    {
        1,  # Ethereum mainnet
        56,  # BSC mainnet
        137,  # Polygon mainnet
        42161,  # Arbitrum One
        10,  # Optimism
        43114,  # Avalanche C-Chain
    }
)

_DEFAULT_FUND_WEI = 10**18  # 1 ETH synthetic funding for depletion drills
_TRANSFER_GAS = 21_000


@dataclass
class WalletCompromiseResult:
    """Outcome of a synthetic local-node wallet depletion drill."""

    validated: bool
    synthetic: bool = True
    target_wallet: str | None = None
    diversion_to: str | None = None
    tx_hash: str | None = None
    chain_id: int | None = None
    rpc_url: str | None = None
    balance_before_wei: int = 0
    balance_after_wei: int = 0
    synthetic_loss_wei: int = 0
    gas_used: int = 0
    gas_price_wei: int = 0
    effective_gas_price_wei: int = 0
    depleted: bool = False
    execution_id: UUID | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LocalBlockchainSandbox:
    """Async Anvil/Hardhat sandbox — synthetic fund diversion only."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._arkham = SamsonArkhamClient(self._settings)
        self._w3: AsyncWeb3 | None = None
        self._rpc_url = str(self._settings.web3_rpc_url).rstrip("/")

    async def __aenter__(self) -> LocalBlockchainSandbox:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def connect(self) -> AsyncWeb3:
        self._assert_local_rpc(self._rpc_url)
        provider = AsyncHTTPProvider(self._rpc_url, request_kwargs={"timeout": 30})
        self._w3 = AsyncWeb3(provider)
        if not await self._w3.is_connected():
            raise ConfigurationError(
                "Local blockchain node unreachable",
                rpc_url=self._rpc_url,
            )
        chain_id = int(await self._w3.eth.chain_id)
        self._assert_safe_chain(chain_id)
        logger.info(
            "LocalBlockchainSandbox connected rpc=%s chain_id=%s",
            self._rpc_url,
            chain_id,
        )
        return self._w3

    async def close(self) -> None:
        if self._w3 is not None:
            provider = self._w3.provider
            # AsyncHTTPProvider exposes an aiohttp session in recent web3 versions.
            session = getattr(provider, "_session", None) or getattr(provider, "session", None)
            if session is not None and hasattr(session, "close"):
                close = session.close()
                if asyncio.iscoroutine(close):
                    await close
            self._w3 = None
        await self._arkham.close()

    @property
    def connected(self) -> bool:
        return self._w3 is not None

    def _w3_or_raise(self) -> AsyncWeb3:
        if self._w3 is None:
            raise ConfigurationError("LocalBlockchainSandbox not connected — call connect() first")
        return self._w3

    @staticmethod
    def _assert_local_rpc(rpc_url: str) -> None:
        parsed = urlparse(rpc_url)
        host = (parsed.hostname or "").lower()
        if not host:
            raise ConfigurationError("Web3 RPC URL missing hostname", rpc_url=rpc_url)
        if host in _LOCAL_RPC_HOSTS:
            return
        # Docker Compose service DNS: single-label hostname on the bridge network.
        if "." not in host and host.replace("-", "").isalnum():
            return
        if host.endswith(".docker.internal"):
            return
        raise ConfigurationError(
            "Refusing non-local Web3 RPC — LocalBlockchainSandbox is sandbox-only",
            rpc_url=rpc_url,
            host=host,
        )

    def _assert_safe_chain(self, chain_id: int) -> None:
        if chain_id in _FORBIDDEN_CHAIN_IDS and not self._settings.web3_allow_mainnet:
            raise ConfigurationError(
                f"Refusing chain_id={chain_id} (mainnet/production). "
                "Use Anvil/Hardhat (e.g. 31337) inside the Docker network.",
                chain_id=chain_id,
            )
        if chain_id == 1 and not self._settings.web3_allow_mainnet:
            raise ConfigurationError("Ethereum mainnet blocked", chain_id=chain_id)

    @staticmethod
    def _normalize_key(private_key: str) -> str:
        key = (private_key or "").strip()
        if not key:
            raise ConfigurationError(
                "SAMSON_WEB3_PRIVATE_KEY / private_key missing for wallet compromise drill",
            )
        if not key.startswith("0x"):
            key = "0x" + key
        return key

    @staticmethod
    def _checksum(w3: AsyncWeb3, address: str) -> str:
        return w3.to_checksum_address(address)

    async def _rpc_set_balance(self, address: str, wei: int) -> None:
        """Anvil/Hardhat cheatcode — no-op on nodes that reject it."""
        w3 = self._w3_or_raise()
        try:
            await w3.provider.make_request(
                "anvil_setBalance",
                [address, hex(wei)],
            )
        except Exception:  # noqa: BLE001
            try:
                await w3.provider.make_request(
                    "hardhat_setBalance",
                    [address, hex(wei)],
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("setBalance cheatcode unavailable: %s", exc)

    async def validate_wallet_compromise(
        self,
        target_wallet: str,
        private_key: str | None = None,
        *,
        operator_id: str = "operator-alpha",
        run_id: UUID | None = None,
        request_id: UUID | None = None,
        execution_id: UUID | None = None,
        fund_wei: int | None = None,
    ) -> WalletCompromiseResult:
        """Simulate fund diversion on the local node and assert balance → 0.

        ``private_key`` defaults to ``SAMSON_WEB3_PRIVATE_KEY`` / settings.
        The key must control ``target_wallet``.
        """
        execution_id = execution_id or uuid4()
        request_id = request_id or uuid4()
        key = self._normalize_key(
            private_key
            if private_key is not None
            else (
                self._settings.web3_private_key
                or os.environ.get("SAMSON_WEB3_PRIVATE_KEY")
                or os.environ.get("WEB3_PRIVATE_KEY")
                or ""
            )
        )

        arkham_intel: ArkhamIntelArtifact | None = None
        try:
            if self._w3 is None:
                await self.connect()
            w3 = self._w3_or_raise()
            chain_id = int(await w3.eth.chain_id)
            self._assert_safe_chain(chain_id)

            account = Account.from_key(key)
            signer = self._checksum(w3, account.address)
            target = self._checksum(w3, target_wallet)
            if signer != target:
                raise ConfigurationError(
                    "Private key does not control target_wallet — refusing diversion",
                    signer=signer,
                    target_wallet=target,
                )

            # Dynamic Balance Profiling — query Arkham before any signer work.
            arkham_intel = await self._profile_address_balance(
                target,
                operator_id=operator_id,
                run_id=run_id,
                request_id=request_id,
            )
            if self._should_skip_signer(arkham_intel, chain_id=chain_id):
                threshold = float(self._settings.arkham_min_balance_usd)
                skipped = WalletCompromiseResult(
                    validated=False,
                    synthetic=True,
                    target_wallet=target,
                    chain_id=chain_id,
                    rpc_url=self._rpc_url,
                    execution_id=execution_id,
                    error=(
                        "arkham_balance_below_threshold: "
                        f"total_balance_usd={arkham_intel.total_balance_usd:.4f} "
                        f"< threshold={threshold:.2f} — signer phase skipped to preserve gas"
                    ),
                    metadata={
                        "skipped_signer": True,
                        "arkham_balance_gate": True,
                        "arkham_min_balance_usd": threshold,
                        "arkham_intel": arkham_intel.model_dump(mode="json"),
                    },
                )
                await asyncio.to_thread(
                    self._persist_emulation_result,
                    skipped,
                    operator_id=operator_id,
                    run_id=run_id,
                    request_id=request_id,
                    arkham_intel=arkham_intel,
                )
                logger.warning(
                    "SKIP signer wallet=%s arkham_balance_usd=%.4f threshold=%.2f",
                    target,
                    arkham_intel.total_balance_usd,
                    threshold,
                )
                return skipped

            diversion_to = self._checksum(w3, self._settings.web3_diversion_to)
            seed = int(fund_wei if fund_wei is not None else _DEFAULT_FUND_WEI)
            if seed > 0:
                await self._rpc_set_balance(target, seed)

            balance_before = int(await w3.eth.get_balance(target))
            if balance_before <= 0:
                raise ConfigurationError(
                    "Target wallet has zero balance on local node after funding attempt",
                    target_wallet=target,
                )

            gas_price = int(await w3.eth.gas_price)
            fee = gas_price * _TRANSFER_GAS
            if balance_before <= fee:
                # Top up so a full drain is possible.
                await self._rpc_set_balance(target, fee + seed)
                balance_before = int(await w3.eth.get_balance(target))
                if balance_before <= fee:
                    raise ConfigurationError(
                        "Insufficient balance to cover gas for synthetic diversion",
                        balance_before=balance_before,
                        fee=fee,
                    )

            value = balance_before - fee
            nonce = int(await w3.eth.get_transaction_count(target, "pending"))
            tx = {
                "nonce": nonce,
                "to": diversion_to,
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

            balance_after = int(await w3.eth.get_balance(target))
            depleted = balance_after == 0
            gas_used = int(receipt.get("gasUsed", _TRANSFER_GAS))
            effective = int(receipt.get("effectiveGasPrice", gas_price) or gas_price)
            loss = max(balance_before - balance_after, 0)

            if not depleted:
                raise AssertionError(
                    f"Asset depletion failed: balance_after={balance_after} wei (expected 0)"
                )

            result = WalletCompromiseResult(
                validated=True,
                synthetic=True,
                target_wallet=target,
                diversion_to=diversion_to,
                tx_hash=tx_hash_hex,
                chain_id=chain_id,
                rpc_url=self._rpc_url,
                balance_before_wei=balance_before,
                balance_after_wei=balance_after,
                synthetic_loss_wei=loss,
                gas_used=gas_used,
                gas_price_wei=gas_price,
                effective_gas_price_wei=effective,
                depleted=True,
                execution_id=execution_id,
                metadata={
                    "status": int(receipt.get("status", 0)),
                    "block_number": int(receipt.get("blockNumber", 0)),
                    "transfer_value_wei": value,
                    "arkham_intel": arkham_intel.model_dump(mode="json") if arkham_intel else None,
                },
            )
            await asyncio.to_thread(
                self._persist_emulation_result,
                result,
                operator_id=operator_id,
                run_id=run_id,
                request_id=request_id,
                arkham_intel=arkham_intel,
            )
            logger.warning(
                "SYNTHETIC wallet compromise validated wallet=%s loss_wei=%s tx=%s depleted=%s",
                target,
                loss,
                tx_hash_hex,
                True,
            )
            return result
        except Exception as exc:  # noqa: BLE001 — keep audit loop alive
            logger.error("validate_wallet_compromise failed: %s", exc)
            failed = WalletCompromiseResult(
                validated=False,
                synthetic=True,
                target_wallet=target_wallet,
                rpc_url=self._rpc_url,
                execution_id=execution_id,
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "arkham_intel": arkham_intel.model_dump(mode="json") if arkham_intel else None,
                },
            )
            try:
                await asyncio.to_thread(
                    self._persist_emulation_result,
                    failed,
                    operator_id=operator_id,
                    run_id=run_id,
                    request_id=request_id,
                    arkham_intel=arkham_intel,
                )
            except Exception as persist_exc:  # noqa: BLE001
                logger.error("Failed to persist synthetic emulation row: %s", persist_exc)
            return failed

    async def _profile_address_balance(
        self,
        address: str,
        *,
        operator_id: str,
        run_id: UUID | None,
        request_id: UUID,
    ) -> ArkhamIntelArtifact | None:
        """Call Arkham balances API; return None only when API key is absent."""
        if not (self._settings.arkham_api_key or "").strip():
            logger.warning(
                "Arkham API key missing — balance gate disabled for %s",
                address,
            )
            return None
        try:
            return await self._arkham.fetch_address_intelligence(
                address,
                operator_id=operator_id,
                run_id=run_id,
                request_id=request_id,
            )
        except Exception as exc:  # noqa: BLE001
            # Fail-open for sandbox continuity; still surface in logs.
            logger.error("Arkham balance profiling failed for %s: %s", address, exc)
            return None

    def _should_skip_signer(
        self,
        intel: ArkhamIntelArtifact | None,
        *,
        chain_id: int,
    ) -> bool:
        if intel is None:
            return False
        if not bool(self._settings.arkham_balance_gate_enabled):
            return False
        if (
            bool(self._settings.arkham_balance_gate_bypass_local_chains)
            and chain_id in _LOCAL_CHAIN_IDS
        ):
            return False
        threshold = float(self._settings.arkham_min_balance_usd)
        return float(intel.total_balance_usd) < threshold

    def _persist_emulation_result(
        self,
        result: WalletCompromiseResult,
        *,
        operator_id: str,
        run_id: UUID | None,
        request_id: UUID,
        arkham_intel: ArkhamIntelArtifact | None = None,
    ) -> None:
        """Insert into adversary_emulation_results with synthetic=True + ArkhamIntelArtifact."""
        execution_id = result.execution_id or uuid4()
        intel_dump = None
        if arkham_intel is not None:
            intel_dump = arkham_intel.model_dump(mode="json")
        elif isinstance(result.metadata.get("arkham_intel"), dict):
            intel_dump = result.metadata.get("arkham_intel")
        payload = {
            "synthetic": True,
            "validation": "local_blockchain_wallet_compromise",
            "target_wallet": result.target_wallet,
            "diversion_to": result.diversion_to,
            "tx_hash": result.tx_hash,
            "chain_id": result.chain_id,
            "rpc_url": result.rpc_url,
            "balance_before_wei": result.balance_before_wei,
            "balance_after_wei": result.balance_after_wei,
            "synthetic_loss_wei": result.synthetic_loss_wei,
            "gas_used": result.gas_used,
            "gas_price_wei": result.gas_price_wei,
            "effective_gas_price_wei": result.effective_gas_price_wei,
            "depleted": result.depleted,
            "validated": result.validated,
            "error": result.error,
            "metadata": result.metadata,
            "arkham_intel": intel_dump,
        }
        entities: list[str] = []
        if result.target_wallet:
            entities.append(result.target_wallet)
        if result.tx_hash:
            entities.append(result.tx_hash)

        embedding: list[float] = [0.0] * 768
        try:
            ollama = OllamaClient(self._settings)
            try:
                embedding = list(ollama.embed(json.dumps(payload, ensure_ascii=False)[:8000]))
            finally:
                ollama.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embedding skipped for synthetic web3 result: %s", exc)

        self._db.execute(
            """
            INSERT INTO adversary_emulation_results (
                execution_id, target_id, payload_id, run_id, request_id, operator_id,
                attack_vector, interface_type, http_status_code, vulnerability_verified,
                response_payload, intercepted_financial_entities, response_embedding,
                rag_document_id, synthetic
            ) VALUES (
                :execution_id, :target_id, :payload_id, :run_id, :request_id, :operator_id,
                :attack_vector, :interface_type, :http_status_code, :vulnerability_verified,
                CAST(:response_payload AS jsonb), :intercepted_financial_entities,
                CAST(:response_embedding AS vector), :rag_document_id, :synthetic
            )
            ON CONFLICT (execution_id) DO UPDATE SET
                response_payload = EXCLUDED.response_payload,
                intercepted_financial_entities = EXCLUDED.intercepted_financial_entities,
                vulnerability_verified = EXCLUDED.vulnerability_verified,
                synthetic = EXCLUDED.synthetic,
                http_status_code = EXCLUDED.http_status_code
            """,
            {
                "execution_id": str(execution_id),
                "target_id": str(uuid4()),
                "payload_id": str(uuid4()),
                "run_id": str(run_id) if run_id else None,
                "request_id": str(request_id),
                "operator_id": operator_id,
                "attack_vector": "Synthetic_Wallet_Compromise",
                "interface_type": "Web3-Local-Sandbox",
                "http_status_code": 200 if result.validated else 500,
                "vulnerability_verified": bool(result.validated and result.depleted),
                "response_payload": json.dumps(payload, ensure_ascii=False),
                "intercepted_financial_entities": entities,
                "response_embedding": vector_literal(embedding),
                "rag_document_id": None,
                "synthetic": True,
            },
        )

        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=request_id,
                tool="validation_node",
                operator_id=operator_id,
                action="validate_wallet_compromise",
                outcome="pass" if result.validated and result.depleted else "fail",
                payload_hash=sha256_payload(payload),
                duration_ms=0,
                run_id=run_id,
            )
