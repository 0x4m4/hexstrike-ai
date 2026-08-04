"""Web3 synthetic diversion signer with hard gas-transaction ceiling.

Signs synthetic fund-diversion transactions on the configured fork / arena RPC
when a purple-team breach is confirmed. Private key is read only from
``SAMSON_WEB3_PRIVATE_KEY`` / settings — never hardcoded.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import httpx

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ConfigurationError

logger = logging.getLogger(__name__)

_GOVERNOR_LOCK = threading.Lock()
_GOVERNOR: GasTransactionGovernor | None = None


@dataclass
class DiversionResult:
    signed: bool
    frozen: bool
    tx_hash: str | None = None
    from_address: str | None = None
    to_address: str | None = None
    gas_used_units: int = 0
    gas_signed_total: int = 0
    gas_remaining: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class GasTransactionGovernor:
    """Process-wide counter + signer enforcing ``max_gas_transactions``."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._lock = threading.Lock()
        self._signed_count = 0
        self._frozen = False
        self._account = None
        self._nonce: int | None = None

    @property
    def signed_count(self) -> int:
        return self._signed_count

    @property
    def gas_remaining(self) -> int:
        return max(int(self._settings.max_gas_transactions) - self._signed_count, 0)

    @property
    def frozen(self) -> bool:
        return self._frozen

    def reset_for_session(self, *, max_gas_transactions: int | None = None) -> None:
        with self._lock:
            if max_gas_transactions is not None:
                self._settings = self._settings.model_copy(
                    update={"max_gas_transactions": int(max_gas_transactions)}
                )
            self._signed_count = 0
            self._frozen = False
            self._nonce = None

    def _load_account(self):
        key = (self._settings.web3_private_key or "").strip()
        if not key:
            raise ConfigurationError(
                "SAMSON_WEB3_PRIVATE_KEY missing — cannot sign synthetic diversion",
            )
        if not key.startswith("0x"):
            key = "0x" + key
        try:
            from eth_account import Account
        except ImportError as exc:
            raise ConfigurationError(
                "eth-account is required for Web3 signing — pip install eth-account",
            ) from exc
        return Account.from_key(key)

    def _rpc(self, method: str, params: list[Any] | None = None) -> Any:
        rpc = str(self._settings.web3_rpc_url).rstrip("/")
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(rpc, json=payload)
            response.raise_for_status()
            body = response.json()
        if "error" in body and body["error"]:
            raise RuntimeError(f"RPC {method} error: {body['error']}")
        return body.get("result")

    def _assert_safe_chain(self, chain_id: int) -> None:
        if chain_id == 1 and not self._settings.web3_allow_mainnet:
            raise ConfigurationError(
                "Refusing Web3 diversion on Ethereum mainnet (chain_id=1); "
                "use fork/arena RPC or set SAMSON_WEB3_ALLOW_MAINNET=true explicitly",
                chain_id=chain_id,
            )

    def sign_synthetic_diversion_on_breach(
        self,
        *,
        operator_id: str,
        run_id: UUID | None,
        request_id: UUID,
        execution_id: UUID,
        target_endpoint: str,
    ) -> DiversionResult:
        """Sign + broadcast one synthetic diversion tx, or freeze at the gas ceiling."""
        with self._lock:
            ceiling = int(self._settings.max_gas_transactions)
            if self._frozen or self._signed_count >= ceiling:
                self._frozen = True
                self._log_freeze(operator_id, run_id, request_id, reason="gas_ceiling_reached")
                return DiversionResult(
                    signed=False,
                    frozen=True,
                    gas_signed_total=self._signed_count,
                    gas_remaining=0,
                    error="web3_pipeline_frozen_max_gas_transactions",
                )

            try:
                account = self._account or self._load_account()
                self._account = account
                chain_id = int(self._settings.web3_chain_id)
                self._assert_safe_chain(chain_id)

                rpc_chain = self._rpc("eth_chainId")
                if rpc_chain is not None:
                    live_chain = int(rpc_chain, 16) if isinstance(rpc_chain, str) else int(rpc_chain)
                    self._assert_safe_chain(live_chain)
                    chain_id = live_chain

                to_addr = (self._settings.web3_diversion_to or "").strip()
                if not to_addr.startswith("0x") or len(to_addr) != 42:
                    raise ConfigurationError("Invalid SAMSON_WEB3_DIVERSION_TO address", to=to_addr)

                # Always re-read pending nonce — LocalBlockchainSandbox may have advanced it.
                nonce_hex = self._rpc("eth_getTransactionCount", [account.address, "pending"])
                nonce = int(nonce_hex, 16)
                self._nonce = nonce

                gas_price_hex = self._rpc("eth_gasPrice")
                gas_price = int(gas_price_hex, 16) if gas_price_hex else 1_000_000_000
                value = int(self._settings.web3_diversion_wei)

                # Ensure dust balance for the 1-wei synthetic diversion (Anvil cheatcode).
                bal_hex = self._rpc("eth_getBalance", [account.address, "latest"])
                bal = int(bal_hex, 16) if bal_hex else 0
                need = value + (gas_price * 21000)
                if bal < need:
                    try:
                        self._rpc("anvil_setBalance", [account.address, hex(need + 10**15)])
                    except Exception:  # noqa: BLE001
                        pass

                tx = {
                    "nonce": nonce,
                    "to": to_addr,
                    "value": value,
                    "gas": 21000,
                    "gasPrice": gas_price,
                    "chainId": chain_id,
                    "data": b"",
                }
                signed = account.sign_transaction(tx)
                raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
                if raw is None:
                    raise RuntimeError("eth_account did not return raw transaction bytes")
                raw_hex = raw.hex()
                if not raw_hex.startswith("0x"):
                    raw_hex = "0x" + raw_hex

                tx_hash = self._rpc("eth_sendRawTransaction", [raw_hex])
                self._nonce = nonce + 1
                self._signed_count += 1
                remaining = max(ceiling - self._signed_count, 0)
                if self._signed_count >= ceiling:
                    self._frozen = True
                    self._log_freeze(operator_id, run_id, request_id, reason="gas_ceiling_hit_after_sign")

                if self._settings.audit_enabled:
                    self._audit.write_redteam_audit(
                        request_id=request_id,
                        tool="web3_gas_governor",
                        operator_id=operator_id,
                        action="sign_synthetic_diversion",
                        outcome="pass",
                        payload_hash=sha256_payload(
                            {
                                "execution_id": str(execution_id),
                                "tx_hash": tx_hash,
                                "from": account.address,
                                "to": to_addr,
                                "value_wei": value,
                                "target_endpoint": target_endpoint,
                            }
                        ),
                        duration_ms=0,
                        run_id=run_id,
                    )

                logger.warning(
                    "WEB3 synthetic diversion signed tx=%s from=%s gas_signed=%s remaining=%s frozen=%s",
                    tx_hash,
                    account.address,
                    self._signed_count,
                    remaining,
                    self._frozen,
                )
                return DiversionResult(
                    signed=True,
                    frozen=self._frozen,
                    tx_hash=str(tx_hash),
                    from_address=account.address,
                    to_address=to_addr,
                    gas_used_units=21000,
                    gas_signed_total=self._signed_count,
                    gas_remaining=remaining,
                    metadata={"chain_id": chain_id, "value_wei": value},
                )
            except Exception as exc:  # noqa: BLE001 — keep audit loop alive
                logger.error("Web3 synthetic diversion failed: %s", exc)
                if self._settings.audit_enabled:
                    self._audit.write_redteam_audit(
                        request_id=request_id,
                        tool="web3_gas_governor",
                        operator_id=operator_id,
                        action="sign_synthetic_diversion",
                        outcome="error",
                        payload_hash=sha256_payload(
                            {"execution_id": str(execution_id), "error": str(exc)}
                        ),
                        duration_ms=0,
                        run_id=run_id,
                    )
                return DiversionResult(
                    signed=False,
                    frozen=self._frozen,
                    gas_signed_total=self._signed_count,
                    gas_remaining=self.gas_remaining,
                    error=f"{type(exc).__name__}: {exc}",
                )

    def _log_freeze(
        self,
        operator_id: str,
        run_id: UUID | None,
        request_id: UUID,
        *,
        reason: str,
    ) -> None:
        logger.warning(
            "WEB3 pipeline FROZEN — signed=%s ceiling=%s reason=%s",
            self._signed_count,
            self._settings.max_gas_transactions,
            reason,
        )
        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=request_id or uuid4(),
                tool="web3_gas_governor",
                operator_id=operator_id,
                action="freeze_web3_pipeline",
                outcome="fail",
                payload_hash=sha256_payload(
                    {
                        "reason": reason,
                        "signed_count": self._signed_count,
                        "max_gas_transactions": self._settings.max_gas_transactions,
                    }
                ),
                duration_ms=0,
                run_id=run_id,
            )


def get_gas_governor(settings: SamsonSettings | None = None) -> GasTransactionGovernor:
    global _GOVERNOR
    with _GOVERNOR_LOCK:
        if _GOVERNOR is None:
            _GOVERNOR = GasTransactionGovernor(settings)
        elif settings is not None:
            _GOVERNOR._settings = settings  # noqa: SLF001 — session knob refresh
        return _GOVERNOR


def reset_gas_governor(*, max_gas_transactions: int | None = None) -> GasTransactionGovernor:
    """Clear signed-tx counter / freeze for a new bulk-audit session."""
    global _GOVERNOR
    with _GOVERNOR_LOCK:
        settings = get_settings()
        if max_gas_transactions is not None:
            settings = settings.model_copy(
                update={"max_gas_transactions": int(max_gas_transactions)}
            )
        _GOVERNOR = GasTransactionGovernor(settings)
        return _GOVERNOR
