# Samson SBM — Production Core Architecture Specification

| Field | Value |
| --- | --- |
| Document ID | `001-core-specification` |
| Status | **Frozen** |
| Version | `1.0.0` |
| Date | 2026-07-16 |
| Branch | `cursor/samson-production-core-f2e6` |
| Runtime verification | Continuous-audit loop **10/10 PASS**; bulk ingestion verified; Docker on-prem stack locked |
| Scope | Production core engine, data contracts, purple-team loop, AI firewall, budget governance, compose topology |

This document freezes the authoritative enterprise architecture for the Samson SBM (Simulation / Purple-Team) production core. All layer descriptions map to concrete modules under `samson/` and the on-premise packaging at repository root. No ADR-006 is introduced by this freeze; prior decisions ADR-002 through ADR-005 remain in force via `docs/decisions/`.

---

## 1. System Context

Samson SBM is an **authorized enterprise AI red-teaming / purple-teaming platform**. The production core:

1. Ingests engagement targets from an operator desktop pool or container fallback path.
2. Optionally enriches IP targets via budget-gated Shodan recon (Postgres cache first).
3. Executes active financial / LLM injection payloads against in-scope HTTP endpoints.
4. Persists emulation evidence with `vector(768)` embeddings for RAG explainability.
5. Compiles and starts an in-process financial guardrail reverse-proxy on port **8787**.
6. Replays the same payload through the proxy (Round 2) and asserts `drop` / `hitl`.
7. Tears down the proxy socket before the next payload index (`deployer.close()`).

Primary runtime entrypoint:

```text
python3 samson/orchestrator.py <command>
```

Container entrypoint is identical (`Dockerfile` → `ENTRYPOINT ["python3", "/workspace/samson/orchestrator.py"]`).

---

## 2. Layered Architecture

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  Operator / CLI / docker compose                                         │
│  run-bulk-audit | run-continuous-audit | shodan-lookup | serve | …     │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│  Continuous Audit & Ingestion Engine                                     │
│  samson/core/target_loader.py  +  samson/orchestrator.py                 │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐   ┌───────────────────┐   ┌──────────────────────────┐
│ Payload       │   │ Async Emulation   │   │ SamsonShodanClient       │
│ Registry      │──▶│ (httpx)           │   │ cache → rate → budget    │
└───────────────┘   └─────────┬─────────┘   └──────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ PostgreSQL 15 +   │
                    │ pgvector          │
                    │ embeddings        │
                    │ vector(768)       │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ RAG Oracle        │
                    │ explainability    │
                    └─────────┬─────────┘
                              │ on breach
                              ▼
                    ┌───────────────────┐
                    │ Guardrail Compiler│
                    │ + Proxy :8787     │
                    │ Round-2 assert    │
                    │ deployer.close()  │
                    └───────────────────┘
```

| Layer | Path | Responsibility |
| --- | --- | --- |
| Data & Schema | `samson/redteam/schemas.py` | Pydantic contracts for emulation, recon, audit, guardrail |
| Ingestion | `samson/core/target_loader.py` | Desktop/container target pool → `IngestedTargetPool` |
| Orchestration | `samson/orchestrator.py` | CLI commands, continuous/bulk audit loops |
| Emulation | `samson/redteam/adversary_executor.py` | Scoped async HTTP execution via httpx |
| RAG | `samson/rag/` | Ingest, retrieve, brief, report with pgvector |
| Guardrail | `samson/redteam/guardrail/` | IBAN validation, HITL queue, aiohttp proxy |
| Recon | `samson/redteam/shodan_collector.py` | Cache-first Shodan client with credit governance |
| Persistence | `samson/migrations/*.sql`, `samson/core/database.py` | Schema + SQLAlchemy pool |
| Packaging | `Dockerfile`, `docker-compose.yml` | On-prem multi-container runtime |

---

## 3. Data & Schema Layer (`samson/redteam/schemas.py`)

All production contracts are Pydantic `BaseModel` types. Field types and semantics below are normative for this freeze.

### 3.1 Core adversary-emulation contracts

#### `AdversaryTargetContext`

Contract for the AI / financial system under test and its network interfaces.

| Field | Type | Semantics |
| --- | --- | --- |
| `target_id` | `UUID` | Stable identity for the engagement target instance |
| `target_endpoint` | `HttpUrl` | Absolute HTTP(S) URL of the model or agent API under audit |
| `interface_type` | `str` | One of `Stripe-Gateway`, `Plaid-Integration`, `REST-LLM-API`, `IBAN-Parser` |
| `auth_headers` | `dict[str, str]` | Authorization headers applied to outbound emulation requests |
| `vector_db_connected` | `bool` | Whether the target path is expected to interact with a vector store (default `False`) |

#### `ExecutionPayload`

Generated payload structure for business-logic resilience testing.

| Field | Type | Semantics |
| --- | --- | --- |
| `payload_id` | `UUID` | Unique payload instance identity |
| `attack_vector` | `str` | Vulnerability class: `Indirect_Prompt_Injection`, `Adversarial_Noise`, or `Context_Bleed` |
| `raw_payload_data` | `str` | Serialized body / injection content sent in the HTTP request |
| `generated_at` | `datetime` | UTC creation timestamp |

#### `AdversaryEmulationResult`

Result of a single network security test execution.

| Field | Type | Semantics |
| --- | --- | --- |
| `execution_id` | `UUID` | Primary key for Postgres `adversary_emulation_results` |
| `vulnerability_verified` | `bool` | `True` when model / agent constraints were bypassed (breach) |
| `http_status_code` | `int` | Upstream HTTP status from the emulation request |
| `response_payload` | `dict[str, Any]` | Raw target response retained for entity extraction and RAG |
| `intercepted_financial_entities` | `list[str]` | IBANs, tokens, masked cards extracted from the response |

#### `GuardrailEnforcementConfig`

Gateway parameters derived from test results and compiled into the live proxy.

| Field | Type | Semantics |
| --- | --- | --- |
| `config_id` | `UUID` | Enforcement configuration identity |
| `strict_regex_patterns` | `list[str]` | Regex patterns blocking credential / IBAN leakage |
| `allowed_destination_hosts` | `list[str]` | Allowlist of domains for outbound AI agent calls |
| `enforce_human_approval` | `bool` | When `True`, mismatch routes to HITL instead of silent drop (default `True`) |

Supporting runtime contracts in the same module include `ProxyMiddlewareConfig`, `GuardrailInterceptionDecision`, `GuardrailPendingAction`, `ContinuousAuditRequest`, `ContinuousAuditResult`, `BulkAuditMatrix`, and `BulkAuditTargetRow`.

### 3.2 Recon contracts

#### `ApiCreditBudget`

PostgreSQL-backed API credit budget and rate-limit state (provider-agnostic shape; Shodan uses `budget_id="shodan_default"`).

| Field | Type | Default / constraint | Semantics |
| --- | --- | --- | --- |
| `budget_id` | `str` | `"shodan_default"` | Logical budget partition |
| `provider` | `str` | `"shodan"` | External OSINT provider key |
| `credits_remaining` | `int` | `ge=0` | Spendable credits left |
| `credits_total` | `int` | `77`, `ge=0` | Initial / ceiling credits |
| `min_interval_sec` | `float` | `5.0`, `gt=0` | Minimum seconds between live queries |
| `last_query_at` | `datetime \| None` | — | Timestamp of last live debit |
| `is_blocked` | `bool` | `False` | Hard block latch |
| `updated_at` | `datetime` | UTC now | Last budget mutation |

#### `ShodanReconArtifact`

Normalized Shodan host intelligence persisted to Postgres and mirrored into RAG markdown under `samson/rag/docs/emulation/`.

| Field | Type | Semantics |
| --- | --- | --- |
| `artifact_id` | `UUID` | Artifact primary key |
| `request_id` | `UUID` | Correlating orchestrator request |
| `ip_address` | `str` | Queried host IP |
| `operator_id` | `str` | Engaging operator |
| `hostnames` | `list[str]` | Reverse / associated hostnames |
| `org` / `isp` / `asn` / `os` | `str \| None` | Org and platform metadata |
| `country_code` / `city` | `str \| None` | Geo fields |
| `open_ports` | `list[int]` | Observed open ports |
| `banners` | `list[ShodanServiceBanner]` | Per-port product/version banners |
| `detected_vulnerabilities` | `list[str]` | CVE identifiers extracted from Shodan vulns arrays |
| `raw_payload` | `dict[str, Any]` | Sanitized raw API payload |
| `rag_doc_path` | `str \| None` | Filesystem path of ingested RAG document |
| `collected_at` | `datetime` | Collection timestamp |

`ShodanCollectResult` wraps an artifact with operational flags: `from_cache`, `credits_spent`, `credits_remaining`, `is_blocked`, `block_reason`.

#### `MetasploitExecutionResult`

Authorized Metasploit Framework module execution result for purple-team recon. This contract captures **defensive engagement telemetry only** (module identity, session outcome, structured findings). It does not encode exploit payloads or weaponization steps.

| Field | Type | Semantics |
| --- | --- | --- |
| `execution_id` | `UUID` | Execution identity |
| `request_id` | `UUID` | Correlating request |
| `operator_id` | `str` | Operator performing the authorized module run |
| `run_id` | `UUID \| None` | Optional exercise run linkage |
| `target_host` | `str` | In-scope IPv4/IPv6 or hostname |
| `target_port` | `int \| None` | Optional service port (`1..65535`) |
| `module_path` | `str` | MSF module path (e.g. `auxiliary/scanner/...`) |
| `module_type` | `Literal[...]` | `auxiliary` (default), `exploit`, `post`, `payload`, `encoder`, `nop` |
| `workspace` | `str` | MSF workspace name (default `samson-default`) |
| `session_established` | `bool` | Whether an MSF session was opened |
| `session_id` | `int \| None` | Session identifier when established |
| `success` | `bool` | Module-level success flag |
| `findings` | `list[str]` | Normalized defensive findings |
| `cve_ids` | `list[str]` | CVE identifiers surfaced by the module |
| `raw_output_hash` | `str \| None` | SHA-256 of sanitized console output for audit correlation |
| `duration_ms` | `int` | Execution duration |
| `error` | `str \| None` | Failure detail when unsuccessful |
| `completed_at` | `datetime` | Completion timestamp |

---

## 4. Continuous Audit & Ingestion Engine

### 4.1 Target ingestion (`samson/core/target_loader.py`)

#### Source resolution order

`TargetLoader.resolve_source_root()` selects the first available root:

1. Explicit `--source-root` / constructor `explicit_root` (when provided).
2. macOS desktop pool: `~/Desktop/тест ЦЕЛИ` (casefold match under `~/Desktop` allowed).
3. Environment override: `SAMSON_TARGETS_DIR` or `SAMSON_TARGET_POOL_DIR`.
4. Container / VPS fallback: `/data/pentest/targets`.

If none exist, a `ConfigurationError` is raised.

#### Document scan and indicator extraction

1. Recursively enumerate text-capable documents (`.txt`, `.md`, `.json`, `.yaml`, `.yml`, `.csv`, `.html`, `.log`, extensionless text, etc.).
2. Decode with UTF-8 / UTF-8-SIG / CP1251 / Latin-1 fallbacks; skip binaries containing NUL.
3. Extract indicators via regex:
   - **URL** — `http://` / `https://`
   - **IPv4** — validated with `ipaddress.IPv4Address`
   - **Domain** — hostname patterns excluding `example.com` / `localhost` noise
4. Deduplicate; prefer URL over bare IP when the same host already appears in a URL.
5. Materialize each unique indicator as `IngestedTarget` and attach an `audit_endpoint` (`HttpUrl`) via `resolve_audit_endpoint()` (HTTP(S) port preference from Shodan open ports when available: `443`, `8443`, `80`, `8080`, …).

#### Output model: `IngestedTargetPool`

| Field | Type | Semantics |
| --- | --- | --- |
| `source_root` | `str` | Absolute path of the scanned pool |
| `scanned_files` | `int` | Successfully read documents |
| `skipped_files` | `int` | Unreadable / binary skipped |
| `targets` | `list[IngestedTarget]` | Unique normalized targets |
| `loaded_at` | `datetime` | Load timestamp |

Each `IngestedTarget` can project into production contracts:

- `to_adversary_context()` → `AdversaryTargetContext`
- `to_continuous_audit_request(...)` → `ContinuousAuditRequest`

#### Scope overlay

Before bulk execution, `write_scope_overlay()` merges ingested targets into a runtime YAML overlay (`config/samson/scope.bulk-overlay.yaml`, gitignored) derived from `config/samson/scope.yaml`, authorizing the engagement window (`allowed_external_egress: true` for the overlay) so `ScopeEnforcer` permits the audited URLs.

### 4.2 Command architecture (`samson/orchestrator.py`)

#### `run-continuous-audit`

Single-target purple-team loop.

```text
CLI args
  → sanitize --target-endpoint (_sanitize_target_endpoint)
  → ContinuousAuditRequest
  → _execute_continuous_audit_loop(settings, req)
  → _print_continuous_audit_metrics(+ optional --json)
  → exit 0 if assertion_passed else 2
```

Critical arguments: `--target-endpoint` (required), `--interface-type`, `--operator`, `--profile`, `--unattended` (default on).

#### `run-bulk-audit`

Multi-target matrix over the ingested pool.

```text
TargetLoader.load()
  → write_scope_overlay() → settings.scope_config_path = overlay
  → for each unique IngestedTarget (optional --limit):
        SamsonShodanClient.fetch_host_data(ip)   # unless --skip-shodan
        resolve_audit_endpoint(open_ports)
        ContinuousAuditRequest from IngestedTarget
        _execute_continuous_audit_loop(...)
  → BulkAuditMatrix + console performance matrix (+ optional --json)
```

Matrix aggregates: Shodan lookups / cache hits / credits spent, payloads executed, breaches, guardrails deployed, proxy verifications / blocks, assertion pass/fail/error counts, and per-target `BulkAuditTargetRow` timing.

---

## 5. The Core Purple Teaming Loop

Implemented by `_execute_continuous_audit_loop` in `samson/orchestrator.py` (production path used by both continuous and bulk commands). Sequence is normative:

### Step 1 — Payload Registry Fetch

`_load_active_payloads()`:

1. Maps `interface_type` → technique allowlist (`_INTERFACE_TECHNIQUES`).
2. Loads active JSON definitions from `PayloadRegistry` (`config/samson/payloads/**/*.json`).
3. Merges catalog entries from `samson/rag/docs/payloads/continuous_audit_payloads.json`.
4. Renders bodies through `PayloadOrchestrator` into `ExecutionPayload` instances.
5. Falls back to `_default_execution_payload` when the registry is empty.

### Step 2 — Async HTTP Emulation Engine (httpx)

For each payload, `AdversaryEmulationExecutor.execute_async()`:

1. Enforces engagement scope via `ScopeEnforcer.assert_url_in_scope`.
2. Issues the authenticated HTTP request with **httpx** against `AdversaryTargetContext.target_endpoint`.
3. Extracts financial entities (`entity_extractor`) into `intercepted_financial_entities`.
4. Returns `AdversaryEmulationResult` with `vulnerability_verified`.

### Step 3 — PostgreSQL Vectorization (`vector(768)`)

On persistence of emulation results / RAG chunks:

- Schema columns `embeddings.embedding vector(768)` (`001_schema.sql`) and `adversary_emulation_results.response_embedding vector(768)` (`002_adversary_emulation.sql`).
- Ollama embedding model produces 768-dimensional vectors stored via pgvector (HNSW cosine index on RAG embeddings).

### Step 4 — RAG Oracle Explainability

`AdversaryEmulationExecutor` / RAG path ingests emulation markdown under `samson/rag/docs/emulation/`, enabling `RagOracle` modes (`retrieve_context`, `build_brief`, `write_report_context`) for operator explainability. Continuous-audit loops may soft-skip chat briefing via `SAMSON_SKIP_RAG_ANALYZE` / `SAMSON_SKIP_RAG_BRIEF` without disabling vector persistence.

### Step 5 — Real-time Guardrail Proxy Compiler

On `vulnerability_verified == True`:

1. `FinancialGuardrailDeployer.deploy_from_execution(...)` compiles `GuardrailEnforcementConfig` + `ProxyMiddlewareConfig` (`GuardrailConfigCompiler`).
2. Persists deployment to `guardrail_proxy_deployments`.
3. Starts `AsyncFinancialGuardrailProxy` on `SAMSON_GUARDRAIL_PROXY_HOST` / `SAMSON_GUARDRAIL_PROXY_PORT` (default `127.0.0.1:8787` in-process; compose long-lived service binds `0.0.0.0:8787`).

### Step 6 — In-process Round 2 Assertion Check

`_rerun_through_proxy()` replays the **same** `ExecutionPayload` through the live proxy listen URL. Assertion rules (`_assert_continuous_audit`):

- No breaches → pipeline **PASS**.
- Each breached step must have `guardrail_deployed` and Round-2 `proxy_verified` with `after_action ∈ {drop, hitl}` → **PASS**; otherwise **FAIL**.

### Step 7 — In-process Socket Cleansing

In a `finally` block after each breached payload’s Round 2:

```text
await deployer.close()
```

This stops the aiohttp `TCPSite` / `AppRunner`, closes the upstream httpx client, clears runtime state, and yields to the event loop so OS port **8787** is released before the next payload index (TIME_WAIT-safe with `reuse_address=True`). An outer `finally` also closes the executor and deployer at loop end.

---

## 6. AI Firewall & Runtime Defenses (`samson/redteam/guardrail/`)

### 6.1 `AsyncFinancialGuardrailProxy`

| Property | Specification |
| --- | --- |
| Module | `samson/redteam/guardrail/proxy_middleware.py` |
| Framework | **aiohttp** `web.Application` reverse-proxy |
| Upstream client | httpx `AsyncClient` |
| Default listen | host from settings / config; production compose → `0.0.0.0:8787` |
| Host publish | `8787:8787` on service `samson-guardrail-proxy` |
| Socket flags | `reuse_address=True`, `reuse_port=False`, `shutdown_timeout=5.0` |
| Catch-all route | `* /{path_info:.*}` → `_handle_request` |

Request path:

1. Read body → UTF-8 text.
2. `inspect_text()` → IBAN + regex policy evaluation.
3. `allow` → forward to `upstream_base_url`.
4. `drop` → HTTP 403 (or configured deny).
5. `hitl` → enqueue `guardrail_pending_actions`, hold / deny pending operator review.

### 6.2 IBANValidator workflow (`iban_validator.py`)

Pure-Python validation — no external IBAN service dependency.

1. **Extract** — regex `\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b` (ISO 13616 structural shape).
2. **Normalize** — strip spaces/hyphens, uppercase.
3. **Whitelist check** — normalized IBAN in compiled frozenset from fixture / deployment config → `VALID_WHITELISTED`.
4. **Checksum** — ISO 13616 **mod-97** (`verify_iban_checksum`); remainder must equal `1`. Chunked modular reduction avoids bigint overflow on long IBANs.
5. **Statuses** — `VALID_WHITELISTED` | `VALID_NOT_WHITELISTED` | `INVALID_FORMAT` | `INVALID_CHECKSUM`.
6. **Outbound evaluation** — `evaluate_outbound_ibans(text, whitelist)` drives proxy decisions; non-whitelisted valid or checksum-invalid IBANs are blocked.

### 6.3 Persistent HITL queue

| Artifact | Detail |
| --- | --- |
| Table | `guardrail_pending_actions` (`003_guardrail_proxy.sql`) |
| Queue API | `samson/redteam/guardrail/hitl_queue.py` → `GuardrailHitlQueue` |
| Statuses | `awaiting_operator_review`, `approved`, `rejected` |
| Key columns | `pending_id`, `deployment_id`, `operator_id`, `run_id`, `intercepted_ibans[]`, `request_body_hash`, `request_path`, `reason`, `operator_note`, `created_at`, `resolved_at` |
| Index | `idx_guardrail_pending_status (status)` |

HITL ensures human authorization for ambiguous financial egress instead of silent allow.

---

## 7. Budget & Rate-Limiting Governance (`SamsonShodanClient`)

Module: `samson/redteam/shodan_collector.py`. Settings knobs: `SAMSON_SHODAN_API_KEY` / `SHODAN_API_KEY`, `shodan_budget_id`, `shodan_initial_credits` (77), `shodan_reserve_credits` (**5**), `shodan_min_interval_sec` (**5.0**).

### Control plane sequence (`fetch_host_data` / `collect_host`)

| Order | Gate | Behavior |
| --- | --- | --- |
| 1 | **Local Postgres cache** | `get_cached_recon(ip)` → on hit return `ShodanCollectResult(from_cache=True, credits_spent=0)` |
| 2 | **API key presence** | Missing key → `ConfigurationError` (live path only) |
| 3 | **Hard credit cutoff** | Block when `credits_remaining <= shodan_reserve_credits` (**`MIN_CREDIT_THRESHOLD = 5`**) or `is_blocked` — emit critical audit, `is_blocked=True`, **no live query** |
| 4 | **Rate limit** | Async lock + monotonic clock; enforce **max 1 live query per 5 seconds** (`min_interval_sec=5.0`) |
| 5 | **Live GET** | `GET {shodan_api_base_url}/shodan/host/{ip}?key=...` via httpx |
| 6 | **Persist + debit** | Write `ShodanReconArtifact`, RAG markdown, debit **1** credit in `ApiCreditBudget` |

This governance guarantees OSINT spend cannot drain below the operational reserve and that repeated bulk audits reuse cache without burning credits.

---

## 8. On-Premise Deployment Architecture

### 8.1 `Dockerfile` (repository root)

| Directive | Specification |
| --- | --- |
| Base image | `python:3.10-slim` |
| Workdir | `/workspace` |
| Env | `PYTHONPATH=/workspace`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1` |
| System deps | `curl`, `libpq5`; build-time `gcc` + `libpq-dev` purged after pip |
| Python deps | `pip install -r requirements-samson.txt` |
| Copy set | `samson/`, `config/`, `target-arena/`, `examples/`, `docker-compose.yml` |
| Import gate | Build `RUN` verifies `import samson, samson.orchestrator, samson.redteam.shodan_collector` |
| Entrypoint | `python3 /workspace/samson/orchestrator.py` |
| Default CMD | `health` |

### 8.2 `docker-compose.yml` topology

Network: `samson_net` (bridge). Volume: `samson_db_data` (named).

| Service | Image / build | Role | Ports | Health / ordering |
| --- | --- | --- | --- | --- |
| `samson-db` | `pgvector/pgvector:pg15` | Postgres 15 + pgvector | `127.0.0.1:5432:5432` | `pg_isready -U samson -d samson -h 127.0.0.1`; interval 5s; retries 30 |
| `samson-core-engine` | build → `samson-sbm:latest` | Orchestrator `serve` (migrate + stay-alive) | — | `depends_on: samson-db: condition: service_healthy` |
| `samson-guardrail-proxy` | build → `samson-sbm:latest` | Long-lived `guardrail-proxy-serve` | `8787:8787` | Same healthy-state dependency on `samson-db` |

Shared environment contract for app services:

```text
SAMSON_DATABASE_URL=postgresql://samson:secret@samson-db:5432/samson
SAMSON_SHODAN_API_KEY / SHODAN_API_KEY  ← host env injection
SAMSON_GUARDRAIL_PROXY_HOST=0.0.0.0
SAMSON_GUARDRAIL_PROXY_PORT=8787
```

Healthy-state rule: **core-engine and guardrail-proxy never start until `pg_isready` reports the database accepts SQL connections.**

Operational note: in-process Round-2 proxy binds `:8787`. When running continuous/bulk audit on the host against a stack that also runs `samson-guardrail-proxy`, stop the compose proxy service for that window (or run audits via `docker exec` into a single owner of the port) to avoid `EADDRINUSE`.

### 8.3 Single-command bring-up

```bash
docker compose up -d --build
# optional Shodan key:
SHODAN_API_KEY=... docker compose up -d
```

Desktop pool bulk audit (Mac / synced VPS):

```bash
python3 samson/orchestrator.py run-bulk-audit --json
# container fallback when desktop path absent:
python3 samson/orchestrator.py run-bulk-audit --source-root /data/pentest/targets --json
```

---

## 9. Persistence Map (normative migrations)

| Migration | Purpose |
| --- | --- |
| `001_schema.sql` | RAG documents/chunks, `embeddings.embedding vector(768)`, exercise runs, audit logs, red-team scan tables |
| `002_adversary_emulation.sql` | `adversary_emulation_results` + `response_embedding vector(768)` |
| `003_guardrail_proxy.sql` | `guardrail_proxy_deployments`, `guardrail_pending_actions` |
| `004_shodan_recon.sql` | `api_credit_budgets`, `shodan_recon_artifacts` |

Applied by `python3 samson/orchestrator.py migrate` and automatically by `serve` / `guardrail-proxy-serve` / audit entry paths that call `cmd_migrate`.

---

## 10. Security & Engagement Constraints

1. **Scope first** — all emulation URLs pass `ScopeEnforcer`; bulk runs use an authorized overlay derived from the ingested pool.
2. **No credential hardcoding** — Shodan keys only via environment (`SAMSON_SHODAN_API_KEY` / `SHODAN_API_KEY`).
3. **Defensive naming** — Metasploit / Shodan contracts store recon telemetry and CVE identifiers; they do not ship exploit PoCs.
4. **HITL default** — `enforce_human_approval=True` with Postgres-backed pending actions for ambiguous IBAN egress.
5. **Credit floor** — Shodan live queries hard-stop at `credits_remaining <= 5`.
6. **Local DB bind** — compose publishes Postgres only on `127.0.0.1:5432`.

---

## 11. Freeze Declaration

This specification freezes the Samson SBM production core architecture as implemented on branch `cursor/samson-production-core-f2e6` at document version `1.0.0`. Changes to contracts in §3, loop ordering in §5, proxy semantics in §6, budget gates in §7, or compose health dependencies in §8 require a superseding `docs/architecture/00x-*.md` revision and an explicit version bump of this document.

**Verification baseline at freeze:** continuous-audit protection loop 10/10 PASS; bulk ingestion → Shodan/cache → payload → guardrail `:8787` Round-2 → matrix output verified; Docker multi-container stack with `pg_isready` healthy-state ordering operational.
