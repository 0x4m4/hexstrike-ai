"""Compile proxy-middleware configuration from adversary emulation database records."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.errors import ConfigurationError
from samson.redteam.guardrail.iban_validator import (
    IbanValidationStatus,
    extract_ibans,
    normalize_iban,
    validate_iban,
)
from samson.redteam.schemas import (
    AdversaryEmulationResult,
    GuardrailEnforcementConfig,
    ProxyMiddlewareConfig,
)

logger = logging.getLogger(__name__)


class GuardrailConfigCompiler:
    """Derives guardrail proxy configuration from emulation results and local whitelist fixtures."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._whitelist_path = self._settings.fixture_root_path / "financial" / "synthetic_ibans.json"
        self._config_output_dir = Path("samson/redteam/guardrail/configs")
        self._config_output_dir.mkdir(parents=True, exist_ok=True)

    def load_iban_whitelist(self) -> frozenset[str]:
        if not self._whitelist_path.is_file():
            raise ConfigurationError(
                f"IBAN whitelist fixture not found: {self._whitelist_path}",
                path=str(self._whitelist_path),
            )
        data = json.loads(self._whitelist_path.read_text(encoding="utf-8"))
        allowed: set[str] = set()
        for merchant in data.get("merchants") or []:
            for iban in merchant.get("allowed_ibans") or []:
                allowed.add(normalize_iban(str(iban)))
        for entry in data.get("ibans") or []:
            label = str(entry.get("label") or "")
            if "PRIMARY" in label.upper() or entry.get("synthetic") is True and "ATTACK" not in label.upper():
                allowed.add(normalize_iban(str(entry.get("iban", ""))))
        allowed.discard("")
        return frozenset(allowed)

    def compile_from_emulation(
        self,
        *,
        emulation: AdversaryEmulationResult,
        execution_id: UUID,
        operator_id: str,
        run_id: UUID | None,
        upstream_base_url: str,
        policy_profile: str = "strict",
    ) -> tuple[ProxyMiddlewareConfig, GuardrailEnforcementConfig]:
        whitelist = self.load_iban_whitelist()
        response_text = json.dumps(emulation.response_payload, ensure_ascii=False)
        entity_text = " ".join(emulation.intercepted_financial_entities)

        all_ibans = extract_ibans(f"{response_text}\n{entity_text}")
        blocked_ibans: list[str] = []
        observed_ibans: list[str] = []

        for iban in all_ibans:
            result = validate_iban(iban, whitelist)
            observed_ibans.append(result.normalized)
            if result.status in {
                IbanValidationStatus.VALID_NOT_WHITELISTED,
                IbanValidationStatus.INVALID_CHECKSUM,
            }:
                blocked_ibans.append(result.normalized)

        for entity in emulation.intercepted_financial_entities:
            if entity.upper().startswith(("DE", "FR", "GB", "NL", "IT", "ES")) and len(entity) >= 15:
                normalized = normalize_iban(entity)
                if normalized and normalized not in whitelist:
                    blocked_ibans.append(normalized)

        blocked_ibans = sorted(set(blocked_ibans))
        blocked_web3 = self._load_arkham_risk_addresses(run_id=run_id)
        # Also block any 0x addresses present in emulation entities that match risk list.
        for entity in emulation.intercepted_financial_entities:
            if isinstance(entity, str) and entity.startswith("0x") and len(entity) == 42:
                if entity.lower() in {a.lower() for a in blocked_web3}:
                    continue
        regex_patterns = self._build_regex_patterns(
            blocked_ibans,
            emulation.intercepted_financial_entities,
            blocked_web3_addresses=blocked_web3,
        )
        allowed_hosts = self._resolve_allowed_hosts()

        enforcement = GuardrailEnforcementConfig(
            config_id=uuid4(),
            strict_regex_patterns=regex_patterns,
            allowed_destination_hosts=allowed_hosts,
            enforce_human_approval=self._settings.require_human_approval,
        )

        proxy_config = ProxyMiddlewareConfig(
            deployment_id=uuid4(),
            execution_id=execution_id,
            run_id=run_id,
            operator_id=operator_id,
            listen_host=self._settings.guardrail_proxy_host,
            listen_port=self._settings.guardrail_proxy_port,
            upstream_base_url=upstream_base_url,
            policy_profile=policy_profile,  # type: ignore[arg-type]
            iban_whitelist=sorted(whitelist),
            blocked_ibans=blocked_ibans,
            observed_ibans=observed_ibans,
            blocked_web3_addresses=blocked_web3,
            strict_regex_patterns=regex_patterns,
            allowed_destination_hosts=allowed_hosts,
            enforce_human_approval=enforcement.enforce_human_approval,
            on_mismatch_action="hitl" if enforcement.enforce_human_approval else "drop",
            guardrail_enforcement=enforcement,
        )

        config_path = self._config_output_dir / f"{proxy_config.deployment_id}.json"
        config_path.write_text(proxy_config.model_dump_json(indent=2) + "\n", encoding="utf-8")
        proxy_config = proxy_config.model_copy(update={"config_path": str(config_path)})
        logger.info(
            "Compiled guardrail config deployment=%s blocked_ibans=%s patterns=%s",
            proxy_config.deployment_id,
            len(blocked_ibans),
            len(regex_patterns),
        )
        return proxy_config, enforcement

    def _load_arkham_risk_addresses(self, *, run_id: UUID | None) -> list[str]:
        """Pull high-risk wallets from web3_recon_artifacts for guardrail blocking."""
        from samson.core.database import Database

        db = Database(self._settings)
        try:
            # Prefer this run's rows, but always include recent high-risk so
            # Shodan→Arkham→Audit→Guardrail stays linked across nested run_ids.
            if run_id is not None:
                rows = db.fetchall(
                    """
                    SELECT DISTINCT address FROM web3_recon_artifacts
                    WHERE is_risk = TRUE
                      AND (
                        run_id = :run_id
                        OR collected_at >= NOW() - INTERVAL '7 days'
                      )
                    """,
                    {"run_id": str(run_id)},
                )
            else:
                rows = db.fetchall(
                    """
                    SELECT DISTINCT address FROM web3_recon_artifacts
                    WHERE is_risk = TRUE
                      AND collected_at >= NOW() - INTERVAL '7 days'
                    """,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Arkham risk address load failed: %s", exc)
            return []
        return sorted({str(r["address"]).lower() for r in rows or [] if r.get("address")})

    def _build_regex_patterns(
        self,
        blocked_ibans: list[str],
        entities: list[str],
        *,
        blocked_web3_addresses: list[str] | None = None,
    ) -> list[str]:
        patterns: list[str] = []
        for iban in blocked_ibans:
            spaced = r"\s*".join(re.escape(ch) for ch in iban)
            patterns.append(spaced)
        for entity in entities:
            if entity.startswith("sk_"):
                patterns.append(re.escape(entity))
            if entity.lower().startswith("bearer "):
                patterns.append(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*")
        for addr in blocked_web3_addresses or []:
            # Case-insensitive 0x…40 hex match
            hex_body = addr[2:] if addr.startswith("0x") else addr
            patterns.append(r"(?i)0x" + "".join(f"[{c}{c.upper()}]" if c.isalpha() else c for c in hex_body.lower()))
        return sorted(set(patterns))

    def _resolve_allowed_hosts(self) -> list[str]:
        from urllib.parse import urlparse

        hosts: set[str] = set()
        for url in (
            self._settings.arena_base_url_str,
            self._settings.resolve_financial_stripe_url(),
            self._settings.resolve_financial_iban_url(),
        ):
            parsed = urlparse(url)
            if parsed.hostname:
                hosts.add(parsed.hostname)
        return sorted(hosts)
