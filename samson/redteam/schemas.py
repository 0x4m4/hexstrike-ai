"""Pydantic schemas for Samson red-team modules.

Core adversary-emulation contract (target context, payloads, execution results,
guardrail config) plus ADR-003 through ADR-005 orchestration schemas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Core adversary-emulation contract (foundation)
# =============================================================================


class AdversaryTargetContext(BaseModel):
    """Contract for the AI system under test and its network interfaces."""

    target_id: UUID
    target_endpoint: HttpUrl = Field(..., description="Real URL of the AI model or agent API under audit")
    interface_type: str = Field(
        ...,
        description="Stripe-Gateway, Plaid-Integration, REST-LLM-API, IBAN-Parser",
    )
    auth_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Authorization tokens and headers for network requests",
    )
    vector_db_connected: bool = False


class ExecutionPayload(BaseModel):
    """Generated payload structure for business-logic resilience testing."""

    payload_id: UUID
    attack_vector: str = Field(
        ...,
        description="Vulnerability class: Indirect_Prompt_Injection, Adversarial_Noise, Context_Bleed",
    )
    raw_payload_data: str = Field(..., description="Raw injection data sent in the HTTP request")
    generated_at: datetime = Field(default_factory=_utcnow)


class AdversaryEmulationResult(BaseModel):
    """Result of a network security test execution."""

    execution_id: UUID
    vulnerability_verified: bool = Field(
        ...,
        description="Whether model constraints were successfully bypassed",
    )
    http_status_code: int
    response_payload: dict[str, Any] = Field(
        ...,
        description="Raw target system response for analysis of extracted data",
    )
    intercepted_financial_entities: list[str] = Field(
        default_factory=list,
        description="Financial identifiers found in response (IBAN, tokens, masked cards)",
    )


class GuardrailEnforcementConfig(BaseModel):
    """Guardrail gateway parameters derived from test results."""

    config_id: UUID
    strict_regex_patterns: list[str] = Field(
        ...,
        description="Regex patterns blocking credential leakage to external networks",
    )
    allowed_destination_hosts: list[str] = Field(
        ...,
        description="Allowlist of domains for outbound AI agent calls",
    )
    enforce_human_approval: bool = True


class ProxyMiddlewareConfig(BaseModel):
    """Compiled local proxy-middleware runtime configuration."""

    deployment_id: UUID
    execution_id: UUID
    run_id: UUID | None = None
    operator_id: str
    listen_host: str
    listen_port: int
    upstream_base_url: str
    policy_profile: Literal["strict", "balanced", "permissive"]
    iban_whitelist: list[str]
    blocked_ibans: list[str]
    observed_ibans: list[str] = Field(default_factory=list)
    blocked_web3_addresses: list[str] = Field(
        default_factory=list,
        description="Arkham high-risk EVM addresses blocked on outbound proxy traffic",
    )
    strict_regex_patterns: list[str]
    allowed_destination_hosts: list[str]
    enforce_human_approval: bool = True
    on_mismatch_action: Literal["drop", "hitl"] = "hitl"
    config_path: str | None = None
    guardrail_enforcement: GuardrailEnforcementConfig | None = None


class GuardrailInterceptionDecision(BaseModel):
    action: Literal["allow", "drop", "hitl"]
    blocked_ibans: list[str]
    blocked_web3_addresses: list[str] = Field(default_factory=list)
    reason: str
    request_path: str
    pending_id: UUID | None = None


class GuardrailPendingAction(BaseModel):
    pending_id: UUID
    deployment_id: UUID
    operator_id: str
    run_id: UUID | None = None
    status: Literal["awaiting_operator_review", "approved", "rejected"]
    intercepted_ibans: list[str]
    request_body_hash: str
    request_path: str
    reason: str
    created_at: datetime
    operator_note: str = ""


class FinancialGuardrailDeployRequest(BaseModel):
    request_id: UUID
    execution_id: UUID
    operator_id: str
    run_id: UUID | None = None
    policy_profile: Literal["strict", "balanced", "permissive"] = "strict"
    upstream_base_url: str | None = None


class FinancialGuardrailDeployResult(BaseModel):
    request_id: UUID
    deployment_id: UUID
    execution_id: UUID
    proxy_config: ProxyMiddlewareConfig
    guardrail_config: GuardrailEnforcementConfig
    listen_url: str
    blocked_ibans: list[str]
    status: Literal["active", "destroyed"]
    completed_at: datetime


class ContinuousAuditRequest(BaseModel):
    request_id: UUID
    target_endpoint: HttpUrl
    interface_type: str = Field(
        default="IBAN-Parser",
        description="Stripe-Gateway, Plaid-Integration, REST-LLM-API, IBAN-Parser",
    )
    operator_id: str
    scenario_id: str = "continuous-audit"
    run_id: UUID | None = None
    auth_headers: dict[str, str] = Field(default_factory=dict)
    rag_query: str | None = None
    rag_top_k: int = Field(default=12, ge=1, le=32)
    policy_profile: Literal["strict", "balanced", "permissive"] = "strict"


class ContinuousAuditStepResult(BaseModel):
    payload_id: UUID
    attack_vector: str
    execution_id: UUID
    breach_verified: bool
    before_http_status: int
    before_allowed: bool = True
    intercepted_financial_entities: list[str] = Field(default_factory=list)
    guardrail_deployed: bool = False
    deployment_id: UUID | None = None
    proxy_listen_url: str | None = None
    after_http_status: int | None = None
    after_action: Literal["allow", "drop", "hitl", "not_run"] = "not_run"
    proxy_verified: bool = False
    proxy_response: dict = Field(default_factory=dict)
    web3_tx_hash: str | None = None
    web3_signed: bool = False
    web3_frozen: bool = False
    gas_remaining: int | None = None
    synthetic_loss_wei: int = 0
    wallet_depleted: bool = False
    validation_tx_hash: str | None = None
    arkham_entity: str | None = None
    arkham_label: str | None = None
    arkham_from_cache: bool | None = None


class ContinuousAuditResult(BaseModel):
    request_id: UUID
    run_id: UUID
    target_endpoint: str
    interface_type: str
    operator_id: str
    payloads_executed: int
    breaches_logged: int
    guardrails_deployed: int
    proxy_verifications: int
    proxy_blocks: int
    rag_metadata: dict
    steps: list[ContinuousAuditStepResult]
    assertion_passed: bool
    completed_at: datetime
    web3_signed_total: int = 0
    gas_remaining: int | None = None
    web3_frozen: bool = False
    synthetic_loss_wei: int = 0
    wallet_depletions: int = 0
    validation_tx_hashes: list[str] = Field(default_factory=list)
    arkham_lookups: int = 0
    arkham_entities: list[str] = Field(default_factory=list)


class BulkAuditTargetRow(BaseModel):
    """One target row in the consolidated bulk-audit performance matrix."""

    target_id: UUID
    kind: str
    normalized_value: str
    audit_endpoint: str | None = None
    ip_address: str | None = None
    open_ports: list[int] = Field(default_factory=list)
    detected_vulnerabilities: list[str] = Field(default_factory=list)
    shodan_from_cache: bool | None = None
    shodan_credits_spent: int = 0
    shodan_blocked: bool = False
    payloads_executed: int = 0
    breaches_logged: int = 0
    guardrails_deployed: int = 0
    proxy_blocks: int = 0
    web3_signed: int = 0
    gas_remaining: int | None = None
    synthetic_loss_wei: int = 0
    wallet_depleted: bool = False
    validation_tx_hash: str | None = None
    arkham_entity: str | None = None
    arkham_label: str | None = None
    arkham_risk: str | None = None
    arkham_is_risk: bool = False
    proxy_status: str = "idle"
    assertion_passed: bool | None = None
    duration_ms: int = 0
    error: str | None = None


class BulkAuditMatrix(BaseModel):
    """Consolidated multi-target continuous-audit performance matrix."""

    request_id: UUID
    operator_id: str
    source_root: str
    interface_type: str
    targets_total: int
    targets_audited: int
    shodan_lookups: int = 0
    shodan_cache_hits: int = 0
    shodan_credits_spent: int = 0
    payloads_executed: int = 0
    breaches_logged: int = 0
    guardrails_deployed: int = 0
    proxy_verifications: int = 0
    proxy_blocks: int = 0
    web3_signed_total: int = 0
    max_gas_transactions: int = 100
    gas_remaining: int | None = None
    web3_frozen: bool = False
    synthetic_loss_wei: int = 0
    wallet_depletions: int = 0
    arkham_lookups: int = 0
    assertion_pass_count: int = 0
    assertion_fail_count: int = 0
    error_count: int = 0
    rows: list[BulkAuditTargetRow] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=_utcnow)


# =============================================================================
# Shodan recon (OSINT host intelligence)
# =============================================================================


class ApiCreditBudget(BaseModel):
    """PostgreSQL-backed Shodan API credit budget and rate-limit state."""

    budget_id: str = "shodan_default"
    provider: str = "shodan"
    credits_remaining: int = Field(..., ge=0)
    credits_total: int = Field(default=77, ge=0)
    min_interval_sec: float = Field(default=5.0, gt=0)
    last_query_at: datetime | None = None
    is_blocked: bool = False
    updated_at: datetime = Field(default_factory=_utcnow)


class ShodanServiceBanner(BaseModel):
    port: int
    transport: str = "tcp"
    product: str | None = None
    version: str | None = None
    banner: str = ""
    timestamp: str | None = None


class ShodanReconArtifact(BaseModel):
    """Normalized Shodan host intelligence for RAG + Postgres persistence."""

    artifact_id: UUID
    request_id: UUID
    ip_address: str
    operator_id: str
    hostnames: list[str] = Field(default_factory=list)
    org: str | None = None
    isp: str | None = None
    asn: str | None = None
    os: str | None = None
    country_code: str | None = None
    city: str | None = None
    open_ports: list[int] = Field(default_factory=list)
    banners: list[ShodanServiceBanner] = Field(default_factory=list)
    detected_vulnerabilities: list[str] = Field(
        default_factory=list,
        description="CVE identifiers extracted from Shodan vulns arrays",
    )
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    rag_doc_path: str | None = None
    collected_at: datetime = Field(default_factory=_utcnow)


class ShodanCollectResult(BaseModel):
    request_id: UUID
    ip_address: str
    is_blocked: bool = False
    block_reason: str | None = None
    from_cache: bool = False
    credits_spent: int = 0
    credits_remaining: int | None = None
    artifact: ShodanReconArtifact | None = None
    http_status_code: int | None = None
    completed_at: datetime = Field(default_factory=_utcnow)


class FofaCollectResult(BaseModel):
    """Outcome of a FOFA hybrid recon lookup (normalized to ShodanReconArtifact)."""

    request_id: UUID
    query: str
    ip_address: str | None = None
    is_blocked: bool = False
    block_reason: str | None = None
    from_cache: bool = False
    credits_spent: int = 0
    credits_remaining: int | None = None
    result_count: int = 0
    artifacts: list[ShodanReconArtifact] = Field(default_factory=list)
    artifact: ShodanReconArtifact | None = None
    http_status_code: int | None = None
    errmsg: str | None = None
    completed_at: datetime = Field(default_factory=_utcnow)


class HybridReconResult(BaseModel):
    """Multi-source recon merge (FOFA Redis hunt ± Shodan host enrich)."""

    request_id: UUID
    operator_id: str
    source_root: str | None = None
    queries: list[str] = Field(default_factory=list)
    targets_considered: int = 0
    fofa_lookups: int = 0
    fofa_cache_hits: int = 0
    fofa_credits_spent: int = 0
    redis_candidates: int = 0
    artifacts: list[ShodanReconArtifact] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    completed_at: datetime = Field(default_factory=_utcnow)


class SweeperAttackResult(BaseModel):
    """Synthetic Anvil-only sweeper attack (BNB-sweeper pattern emulation)."""

    execution_id: UUID
    request_id: UUID
    synthetic: bool = True
    sandbox_only: bool = True
    watched_wallet: str
    destination_wallet: str
    triggered: bool = False
    swept: bool = False
    balance_before_wei: int = 0
    balance_after_wei: int = 0
    swept_wei: int = 0
    min_sweep_wei: int = 0
    gas_price_wei: int = 0
    tx_hash: str | None = None
    chain_id: int | None = None
    rpc_url: str | None = None
    pattern_id: str = "bnb_sweeper_full_balance_drain"
    error: str | None = None
    completed_at: datetime = Field(default_factory=_utcnow)


class SweeperDefenseResult(BaseModel):
    """Defensive detection + guardrail block for sweeper destination wallets."""

    detection_id: UUID
    request_id: UUID
    detected: bool = False
    blocked: bool = False
    risk_level: str = "unknown"
    destination_wallet: str | None = None
    watched_wallet: str | None = None
    indicators: list[str] = Field(default_factory=list)
    guardrail_loaded: bool = False
    persisted_web3_recon: bool = False
    remediation: list[str] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=_utcnow)


class SweeperPurpleTeamResult(BaseModel):
    """Two-sided purple-team loop: synthetic sweeper attack → defense assertion."""

    request_id: UUID
    operator_id: str
    attack: SweeperAttackResult
    defense: SweeperDefenseResult
    assertion_passed: bool = False
    completed_at: datetime = Field(default_factory=_utcnow)


class DrainerFamilyResult(BaseModel):
    """One family in the multi-drainer purple-team suite (evm / usdt / trx)."""

    family: Literal["evm_erc20", "usdt_evm", "trx_trc20"]
    source_repo: str
    synthetic: bool = True
    sandbox_only: bool = True
    attack_executed: bool = False
    attack_success: bool = False
    defense_detected: bool = False
    defense_blocked: bool = False
    victim_wallet: str | None = None
    destination_wallet: str | None = None
    token_address: str | None = None
    token_symbol: str | None = None
    amount_raw: int = 0
    approve_tx: str | None = None
    drain_tx: str | None = None
    indicators: list[str] = Field(default_factory=list)
    remediation: list[str] = Field(default_factory=list)
    error: str | None = None


class DrainerPurpleTeamResult(BaseModel):
    """Suite covering EVM/USDT/TRX drainer patterns — attack (sandbox) + defense."""

    request_id: UUID
    operator_id: str
    families_run: list[str] = Field(default_factory=list)
    results: list[DrainerFamilyResult] = Field(default_factory=list)
    assertion_passed: bool = False
    completed_at: datetime = Field(default_factory=_utcnow)


class CoinStatsTokenBalance(BaseModel):
    """Normalized token holding from CoinStats wallet balance API."""

    coin_id: str | None = None
    name: str | None = None
    symbol: str | None = None
    amount: float = 0.0
    price_usd: float | None = None
    value_usd: float | None = None
    chain: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class CoinStatsWalletArtifact(BaseModel):
    """Public wallet OSINT snapshot via CoinStats (read-only)."""

    artifact_id: UUID
    request_id: UUID
    operator_id: str
    address: str
    connection_id: str
    is_empty: bool = True
    token_count: int = 0
    total_value_usd: float = 0.0
    balances: list[CoinStatsTokenBalance] = Field(default_factory=list)
    transactions_synced: bool = False
    transaction_count: int = 0
    transactions: list[dict[str, Any]] = Field(default_factory=list)
    defi_raw: dict[str, Any] | list[Any] | None = None
    from_cache: bool = False
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=_utcnow)
    error: str | None = None


class CoinStatsCollectResult(BaseModel):
    """Outcome of a CoinStats wallet lookup."""

    request_id: UUID
    address: str
    connection_id: str
    artifact: CoinStatsWalletArtifact | None = None
    from_cache: bool = False
    credits_hint: int | None = None
    error: str | None = None
    completed_at: datetime = Field(default_factory=_utcnow)


class ArkhamEntityRef(BaseModel):
    """Normalized Arkham entity attribution for an address."""

    entity_id: str | None = None
    name: str | None = None
    entity_type: str | None = None
    website: str | None = None
    twitter: str | None = None
    note: str | None = None


class ArkhamChainIntelligence(BaseModel):
    """Per-chain Arkham intelligence slice for one address."""

    chain: str
    address: str
    label_name: str | None = None
    is_contract: bool | None = None
    is_user_address: bool | None = None
    entity: ArkhamEntityRef | None = None


class ArkhamAddressArtifact(BaseModel):
    """Cached Arkham address intelligence for RAG + Postgres persistence."""

    artifact_id: UUID
    request_id: UUID
    operator_id: str
    address: str
    primary_chain: str | None = None
    entity_name: str | None = None
    entity_id: str | None = None
    entity_type: str | None = None
    label_name: str | None = None
    is_contract: bool | None = None
    is_user_address: bool | None = None
    chains_seen: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    chain_intel: list[ArkhamChainIntelligence] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    rag_doc_path: str | None = None
    collected_at: datetime = Field(default_factory=_utcnow)


class ArkhamCollectResult(BaseModel):
    """Outcome of an Arkham address intelligence lookup."""

    request_id: UUID
    address: str
    from_cache: bool = False
    http_status_code: int | None = None
    artifact: ArkhamAddressArtifact | None = None
    error: str | None = None
    completed_at: datetime = Field(default_factory=_utcnow)


class ArkhamIntelArtifact(BaseModel):
    """Production Arkham Intel profile used for balance gating and explainability."""

    address: str
    entity_name: str | None = Field(
        default=None,
        description="Real-world owner name annotated by Arkham",
    )
    labels: list[str] = Field(default_factory=list)
    total_balance_usd: float = 0.0
    active_chains: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=_utcnow)
    entity_id: str | None = None
    entity_type: str | None = None
    balance_by_chain_usd: dict[str, float] = Field(default_factory=dict)
    raw_balances_payload: dict[str, Any] = Field(default_factory=dict)
    http_status_code: int | None = None
    from_cache: bool = False


class RedisTrophySample(BaseModel):
    """One AI/LLM-related Redis key with a truncated sample value."""

    key: str
    pattern_matched: str
    value_type: str = "string"
    sample_value: str = ""
    value_bytes: int = 0


class RedisEmulationResult(BaseModel):
    """Result of an authorized unauthenticated Redis resilience probe."""

    execution_id: UUID
    request_id: UUID
    operator_id: str
    run_id: UUID | None = None
    target_host: str
    target_port: int = Field(default=6379, ge=1, le=65535)
    connected: bool = False
    authentication_required: bool = False
    vulnerability_verified: bool = False
    redis_version: str | None = None
    keys_scanned: int = 0
    compromised_key_count: int = 0
    intercepted_contexts: list[str] = Field(default_factory=list)
    trophy_samples: list[RedisTrophySample] = Field(default_factory=list)
    rag_doc_path: str | None = None
    rag_document_id: UUID | None = None
    duration_ms: int = Field(default=0, ge=0)
    error: str | None = None
    completed_at: datetime = Field(default_factory=_utcnow)


class MetasploitExecutionResult(BaseModel):
    """Authorized Metasploit Framework module execution result for purple-team recon.

    Captures defensive engagement telemetry only: module identity, session outcome,
    and structured findings. Does not encode exploit payloads or weaponization steps.
    """

    execution_id: UUID
    request_id: UUID
    operator_id: str
    run_id: UUID | None = None
    target_host: str = Field(..., description="Authorized IPv4/IPv6 or hostname in engagement scope")
    target_port: int | None = Field(default=None, ge=1, le=65535)
    module_path: str = Field(
        ...,
        description="MSF module path used under authorized engagement (e.g. auxiliary/scanner/...)",
    )
    module_type: Literal["auxiliary", "exploit", "post", "payload", "encoder", "nop"] = "auxiliary"
    workspace: str = "samson-default"
    session_established: bool = False
    session_id: int | None = None
    success: bool = False
    findings: list[str] = Field(
        default_factory=list,
        description="Normalized defensive findings (open services, versions, CVE hints)",
    )
    cve_ids: list[str] = Field(default_factory=list)
    raw_output_hash: str | None = Field(
        default=None,
        description="SHA-256 of sanitized console output for audit correlation",
    )
    duration_ms: int = Field(default=0, ge=0)
    error: str | None = None
    completed_at: datetime = Field(default_factory=_utcnow)


# =============================================================================
# ADR-003 PyRIT
# =============================================================================


class PyRITRiskRequest(BaseModel):
    request_id: UUID
    scenario_id: str
    scenario_draft: dict
    atlas_techniques: list[str] = Field(default_factory=list)
    target_profile: dict = Field(default_factory=dict)
    environment: Literal["dev", "stage", "prod"]
    operator_id: str
    target_context: AdversaryTargetContext | None = None


class PyRITRiskResult(BaseModel):
    request_id: UUID
    risk_score: float
    risk_band: Literal["low", "medium", "high", "critical"]
    harm_categories: list[str]
    blocked: bool
    requires_elevated_approval: bool
    rationale: str
    pyrit_report_path: str
    scanned_at: datetime


# =============================================================================
# ADR-003 Garak
# =============================================================================


class GarakScanRequest(BaseModel):
    request_id: UUID
    model_endpoint: str
    model_name: str
    probe_suite: Literal["full", "fast", "custom"] = "fast"
    environment: Literal["dev", "stage", "prod"]
    triggered_by: Literal["schedule", "model_change", "pre_exercise", "manual"]
    target_context: AdversaryTargetContext | None = None


class GarakFinding(BaseModel):
    probe_name: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    description: str
    evidence: str
    mitre_atlas_technique: str | None = None


class GarakScanResult(BaseModel):
    request_id: UUID
    scan_id: UUID
    model_name: str
    probes_run: int
    probes_failed: int
    hit_rate: float
    findings: list[GarakFinding]
    garak_report_path: str
    scanned_at: datetime


# =============================================================================
# ADR-003 ATLAS
# =============================================================================


class ATLASMapRequest(BaseModel):
    request_id: UUID
    artifact_type: Literal["scenario_draft", "telemetry", "garak_finding", "pyrit_report", "financial_impact"]
    artifact: dict
    top_k: int = 5


class ATLASEntry(BaseModel):
    atlas_id: str
    name: str
    description: str
    confidence: float
    evidence: str


class ATLASMapResult(BaseModel):
    request_id: UUID
    tactics: list[ATLASEntry]
    techniques: list[ATLASEntry]
    mitigations: list[str]
    confidence: float
    taxonomy_version: str


# =============================================================================
# ADR-004 Impact
# =============================================================================


class ImpactSimulationRequest(BaseModel):
    request_id: UUID
    run_id: UUID
    operator_id: str
    scenario_id: str
    atlas_techniques: list[str] = Field(default_factory=list)
    arena_target_id: str
    simulation_profile: Literal["persistence", "data_access", "lateral_movement", "full_chain", "financial_impact"]
    environment: Literal["dev", "stage", "prod"]
    payload_ids: list[str] = Field(default_factory=list)
    variables: dict = Field(default_factory=dict)
    target_context: AdversaryTargetContext | None = None
    execution_payloads: list[ExecutionPayload] = Field(default_factory=list)


class ImpactSimulationResult(BaseModel):
    request_id: UUID
    simulation_id: UUID
    run_id: UUID
    phases_executed: list[str]
    synthetic_artifacts_accessed: list[str]
    atlas_mappings: list[str]
    impact_summary: str
    reversible: bool
    audit_path: str
    payload_results: list[dict] = Field(default_factory=list)
    emulation_results: list[AdversaryEmulationResult] = Field(default_factory=list)
    completed_at: datetime


class RemediationDemoRequest(BaseModel):
    request_id: UUID
    run_id: UUID
    simulation_id: UUID | None = None
    operator_id: str
    demo_type: Literal["impact_protection_report", "remediation_walkthrough", "guardrail_container"]
    audience: Literal["operator", "leadership", "blue_team"]
    guardrail_config: GuardrailEnforcementConfig | None = None


class RemediationDemoResult(BaseModel):
    request_id: UUID
    demo_id: UUID
    report_id: UUID
    report_path: str
    guardrail_deployment_id: UUID | None = None
    pyrit_post_score: float | None = None
    citations: list[str]
    guardrail_config: GuardrailEnforcementConfig | None = None
    completed_at: datetime


# =============================================================================
# ADR-005 Financial
# =============================================================================


class FinancialSandboxRequest(BaseModel):
    request_id: UUID
    run_id: UUID
    operator_id: str
    scenario_id: str
    technique: Literal["invoice_substitution", "payment_api_abuse", "beneficiary_swap", "llm_payment_injection"]
    mock_merchant_id: str
    environment: Literal["dev", "stage", "prod"]
    payload_id: str | None = None
    variables: dict = Field(default_factory=dict)
    target_context: AdversaryTargetContext | None = None
    execution_payload: ExecutionPayload | None = None


class FinancialSandboxResult(BaseModel):
    request_id: UUID
    simulation_id: UUID
    technique: str
    mock_transactions: list[dict]
    synthetic_amount_eur: float
    substitution_detected: bool
    ledger_snapshot_path: str
    atlas_technique_ids: list[str]
    payload_results: list[dict] = Field(default_factory=list)
    emulation_result: AdversaryEmulationResult | None = None
    completed_at: datetime


class FinancialGuardrailRequest(BaseModel):
    request_id: UUID
    run_id: UUID
    simulation_id: UUID
    operator_id: str
    action: Literal["deploy", "test", "teardown"]
    policy_profile: Literal["strict", "balanced", "permissive"]
    guardrail_config: GuardrailEnforcementConfig | None = None
    execution_id: UUID | None = None


class FinancialGuardrailResult(BaseModel):
    request_id: UUID
    deployment_id: UUID
    action: str
    rules_applied: list[str]
    pre_block_events: int
    post_block_events: int
    pyrit_post_score: float | None = None
    status: Literal["active", "teardown", "destroyed"]
    guardrail_config: GuardrailEnforcementConfig | None = None
    completed_at: datetime


__all__ = [
    "AdversaryTargetContext",
    "ExecutionPayload",
    "AdversaryEmulationResult",
    "GuardrailEnforcementConfig",
    "ProxyMiddlewareConfig",
    "GuardrailInterceptionDecision",
    "GuardrailPendingAction",
    "FinancialGuardrailDeployRequest",
    "FinancialGuardrailDeployResult",
    "ContinuousAuditRequest",
    "ContinuousAuditStepResult",
    "ContinuousAuditResult",
    "BulkAuditTargetRow",
    "BulkAuditMatrix",
    "ApiCreditBudget",
    "ShodanServiceBanner",
    "ShodanReconArtifact",
    "ShodanCollectResult",
    "FofaCollectResult",
    "HybridReconResult",
    "SweeperAttackResult",
    "SweeperDefenseResult",
    "SweeperPurpleTeamResult",
    "DrainerFamilyResult",
    "DrainerPurpleTeamResult",
    "CoinStatsTokenBalance",
    "CoinStatsWalletArtifact",
    "CoinStatsCollectResult",
    "ArkhamEntityRef",
    "ArkhamChainIntelligence",
    "ArkhamAddressArtifact",
    "ArkhamCollectResult",
    "ArkhamIntelArtifact",
    "RedisTrophySample",
    "RedisEmulationResult",
    "MetasploitExecutionResult",
    "PyRITRiskRequest",
    "PyRITRiskResult",
    "GarakScanRequest",
    "GarakFinding",
    "GarakScanResult",
    "ATLASMapRequest",
    "ATLASEntry",
    "ATLASMapResult",
    "ImpactSimulationRequest",
    "ImpactSimulationResult",
    "RemediationDemoRequest",
    "RemediationDemoResult",
    "FinancialSandboxRequest",
    "FinancialSandboxResult",
    "FinancialGuardrailRequest",
    "FinancialGuardrailResult",
]
