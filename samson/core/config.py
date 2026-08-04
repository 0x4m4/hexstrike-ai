"""Environment-driven configuration for Samson SBM. No hardcoded endpoints or credentials."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# hexstrike-ai repository root (samson/core/config.py -> parents[2])
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Local Docker Compose PostgreSQL (used when SAMSON_DATABASE_URL is unset)
_LOCAL_DOCKER_DATABASE_URL = "postgresql://samson:secret@127.0.0.1:5432/samson"


def repo_root() -> Path:
    return _REPO_ROOT


def _default_repo_path(*parts: str) -> Path:
    return _REPO_ROOT.joinpath(*parts)


class SamsonSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SAMSON_",
        extra="ignore",
    )

    # Identity
    project: str = Field(default="samson-sbm", description="Project / tenant identifier")
    environment: Literal["dev", "stage", "prod"] = "dev"

    # PostgreSQL — defaults to local Docker Compose credentials
    database_url: str = Field(
        default=_LOCAL_DOCKER_DATABASE_URL,
        description="SQLAlchemy-compatible PostgreSQL URL (Docker Compose local default)",
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_sec: int = 30

    # Ollama / LLM
    ollama_base_url: HttpUrl = Field(default="http://127.0.0.1:11434")
    ollama_embed_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3.2"
    ollama_timeout_sec: float = 120.0

    # Target Arena — authorized scope endpoints (from env / config, never hardcoded in code)
    arena_base_url: HttpUrl = Field(default="http://127.0.0.1:8080")
    arena_namespace: str = "samson-arena"
    financial_mock_stripe_url: HttpUrl | None = None
    financial_mock_iban_url: HttpUrl | None = None

    # Scope & payloads (repo-absolute defaults; relative env values resolve against repo root)
    scope_config_path: Path = Field(default_factory=lambda: _default_repo_path("config", "samson", "scope.yaml"))
    payload_registry_path: Path = Field(default_factory=lambda: _default_repo_path("config", "samson", "payloads"))
    fixture_root_path: Path = Field(default_factory=lambda: _default_repo_path("target-arena", "fixtures"))

    # RAG
    rag_chunk_size_tokens: int = 512
    rag_chunk_overlap_tokens: int = 64
    rag_docs_path: Path = Field(default_factory=lambda: _default_repo_path("samson", "rag", "docs"))
    rag_reports_path: Path = Field(default_factory=lambda: _default_repo_path("samson", "rag", "reports"))
    rag_index_version: int = 1

    # Red team tools
    pyrit_enabled: bool = True
    pyrit_config_path: Path = Field(default_factory=lambda: _default_repo_path("config", "samson", "pyrit.yaml"))
    pyrit_python: str = "python3"
    pyrit_block_threshold: float = 0.8
    pyrit_elevated_threshold: float = 0.6

    garak_enabled: bool = True
    garak_probe_suite: Literal["full", "fast", "custom"] = "fast"
    garak_reports_path: Path = Field(
        default_factory=lambda: _default_repo_path("samson", "redteam", "garak", "reports")
    )

    atlas_taxonomy_path: Path = Field(
        default_factory=lambda: _default_repo_path("samson", "redteam", "atlas", "taxonomy.json")
    )

    # HTTP client
    http_timeout_sec: float = 30.0
    http_connect_timeout_sec: float = 10.0
    http_max_retries: int = 3
    http_retry_backoff_sec: float = 1.5
    http_user_agent: str = "Samson-SBM/0.1.0 (Authorized-Red-Team)"

    # Audit
    audit_enabled: bool = True

    # Execution gate
    require_human_approval: bool = True
    prod_dual_approval: bool = True

    # Financial guardrail proxy (ADR-004/005 runtime)
    guardrail_proxy_host: str = "127.0.0.1"
    guardrail_proxy_port: int = 8787
    guardrail_proxy_auto_start: bool = True

    # Shodan OSINT recon (key via SAMSON_SHODAN_API_KEY — never hardcode)
    shodan_api_key: str = ""
    shodan_api_base_url: HttpUrl = Field(default="https://api.shodan.io")
    shodan_budget_id: str = "shodan_default"
    shodan_min_interval_sec: float = 5.0
    shodan_initial_credits: int = 77
    shodan_reserve_credits: int = 5

    # Web3 / EVM synthetic diversion (key via SAMSON_WEB3_PRIVATE_KEY — never hardcode)
    web3_private_key: str = ""
    web3_rpc_url: HttpUrl = Field(default="http://127.0.0.1:8545")
    web3_chain_id: int = 31337
    web3_diversion_to: str = "0x000000000000000000000000000000000000dEaD"
    web3_diversion_wei: int = 1
    max_gas_transactions: int = 100
    web3_allow_mainnet: bool = False

    # Arkham Intel on-chain OSINT (key via SAMSON_ARKHAM_API_KEY — never hardcode)
    arkham_api_key: str = ""
    arkham_api_base_url: HttpUrl = Field(default="https://api.arkm.com")
    arkham_min_interval_sec: float = 1.0
    arkham_cache_ttl_sec: int = 86_400
    # Skip Web3 signer when Arkham total_balance_usd is below this USD threshold.
    arkham_min_balance_usd: float = 10.0
    arkham_balance_gate_enabled: bool = True
    # Local Anvil/Hardhat drills keep gas free — still fetch+persist, but do not skip signer.
    arkham_balance_gate_bypass_local_chains: bool = True

    # FOFA hybrid OSINT recon (key via SAMSON_FOFA_API_KEY — never hardcode)
    fofa_api_key: str = ""
    fofa_api_email: str = ""
    fofa_api_base_url: HttpUrl = Field(default="https://fofa.info")
    fofa_budget_id: str = "fofa_default"
    fofa_min_interval_sec: float = 5.0
    fofa_cache_ttl_sec: int = 86_400
    fofa_initial_credits: int = 100
    fofa_reserve_credits: int = 0
    fofa_default_size: int = 100

    # CoinStats public wallet OSINT (key via SAMSON_COINSTATS_API_KEY — never hardcode)
    coinstats_api_key: str = ""
    coinstats_api_base_url: HttpUrl = Field(default="https://api.coinstats.app/v1")
    coinstats_min_interval_sec: float = 1.0
    coinstats_cache_ttl_sec: int = 86_400

    @field_validator("shodan_api_key", mode="before")
    @classmethod
    def _coerce_shodan_api_key(cls, value: object) -> str:
        import os

        text = str(value or "").strip()
        if text:
            return text
        return (os.environ.get("SHODAN_API_KEY") or "").strip()

    @field_validator("web3_private_key", mode="before")
    @classmethod
    def _coerce_web3_private_key(cls, value: object) -> str:
        import os

        text = str(value or "").strip()
        if text:
            return text
        return (os.environ.get("SAMSON_WEB3_PRIVATE_KEY") or os.environ.get("WEB3_PRIVATE_KEY") or "").strip()

    @field_validator("arkham_api_key", mode="before")
    @classmethod
    def _coerce_arkham_api_key(cls, value: object) -> str:
        import os

        text = str(value or "").strip()
        if text:
            return text
        return (
            os.environ.get("SAMSON_ARKHAM_API_KEY")
            or os.environ.get("ARKHAM_API_KEY")
            or ""
        ).strip()

    @field_validator("fofa_api_key", mode="before")
    @classmethod
    def _coerce_fofa_api_key(cls, value: object) -> str:
        import os

        text = str(value or "").strip()
        if text:
            return text
        return (
            os.environ.get("SAMSON_FOFA_API_KEY")
            or os.environ.get("FOFA_API_KEY")
            or ""
        ).strip()

    @field_validator("fofa_api_email", mode="before")
    @classmethod
    def _coerce_fofa_api_email(cls, value: object) -> str:
        import os

        text = str(value or "").strip()
        if text:
            return text
        return (
            os.environ.get("SAMSON_FOFA_API_EMAIL")
            or os.environ.get("FOFA_EMAIL")
            or ""
        ).strip()

    @field_validator("coinstats_api_key", mode="before")
    @classmethod
    def _coerce_coinstats_api_key(cls, value: object) -> str:
        import os

        text = str(value or "").strip()
        if text:
            return text
        return (
            os.environ.get("SAMSON_COINSTATS_API_KEY")
            or os.environ.get("COINSTATS_API_KEY")
            or ""
        ).strip()

    @field_validator(
        "scope_config_path",
        "payload_registry_path",
        "fixture_root_path",
        "rag_docs_path",
        "rag_reports_path",
        "pyrit_config_path",
        "garak_reports_path",
        "atlas_taxonomy_path",
        mode="before",
    )
    @classmethod
    def _coerce_path(cls, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = _REPO_ROOT / path
        return path

    @field_validator("database_url", mode="before")
    @classmethod
    def _coerce_database_url(cls, value: object) -> str:
        if value is None:
            return _LOCAL_DOCKER_DATABASE_URL
        text = str(value).strip()
        if not text:
            return _LOCAL_DOCKER_DATABASE_URL
        return text

    @property
    def ollama_base_url_str(self) -> str:
        return str(self.ollama_base_url).rstrip("/")

    @property
    def arena_base_url_str(self) -> str:
        return str(self.arena_base_url).rstrip("/")

    def resolve_financial_stripe_url(self) -> str:
        if self.financial_mock_stripe_url is not None:
            return str(self.financial_mock_stripe_url).rstrip("/")
        return f"{self.arena_base_url_str}/mock-stripe"

    def resolve_financial_iban_url(self) -> str:
        if self.financial_mock_iban_url is not None:
            return str(self.financial_mock_iban_url).rstrip("/")
        return f"{self.arena_base_url_str}/mock-iban-validator"


@lru_cache
def get_settings() -> SamsonSettings:
    return SamsonSettings()
