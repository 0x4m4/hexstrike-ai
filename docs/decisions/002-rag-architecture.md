# ADR-002: RAG Architecture for Samson SBM

## Status

Accepted

## Date

2026-07-16

## Context

Samson SBM is a purple-team simulation platform composed of an Orchestrator, simulation agents, a Target Arena, Ollama Core for scenario drafting, and monitoring/telemetry. Without retrieval-augmented generation (RAG), agents operate without institutional memory: they cannot reference prior exercises, playbooks, findings, or remediation guidance when proposing or explaining scenarios.

We need a RAG layer that:

- Provides **context** for scenario drafting and operator briefings
- Enables **explainability** via citations and evidence links
- Supports **audit and reporting** for exercise cycles
- Accumulates **project memory** across runs
- Operates under **defensive guardrails** — RAG must not become an autonomous offensive execution engine

RAG in Samson SBM is a **contextual orchestration engine**, not a weaponization assistant. All retrieval and generation outputs feed into policy validation and human approval before any simulation runs in the Target Arena.

## Decision

Implement a dedicated RAG layer at `samson/rag/` with:

1. A single service entry point: `rag_oracle.py` (three modes: `retrieve_context`, `build_brief`, `write_report_context`)
2. PostgreSQL + **pgvector** for document metadata, chunks, embeddings, exercise history, and citations
3. A pipeline split across `search/ingest.py`, `search/retrieve.py`, and `search/rerank.py`
4. Mandatory guardrails: scope enforcement, explainability, audit trail, and index versioning
5. Integration into the Orchestrator workflow **before** scenario approval and **after** telemetry for memory updates

### Directory layout

```text
samson/
  rag/
    docs/          # knowledge base (markdown, json, pdf-derived text)
    index/         # local indexing artifacts (dev); production uses Postgres
    reports/       # exercise reports and audit outputs
    search/
      ingest.py    # chunking, normalization, embeddings, re-index
      retrieve.py  # semantic retrieval + metadata filters
      rerank.py    # reranking and top-k explanation
    rag_oracle.py  # Orchestrator-facing service API
    schemas.py     # Pydantic models, SQL DDL helpers, pgvector types
```

### Orchestrator integration workflow

```text
Detection Agent
  -> RAG Oracle (retrieve_context)
  -> Scenario Draft (Ollama Core)
  -> Scope / Policy Validation
  -> Human Approval
  -> Simulation Runner (Target Arena only)
  -> Telemetry Agent
  -> Report Writer (write_report_context)
  -> RAG Memory Update (ingest.py)
```

RAG Oracle is invoked at two mandatory points:

| Phase | Mode | Purpose |
|---|---|---|
| Pre-scenario | `retrieve_context` → `build_brief` | Supply grounded context to Ollama Core and the operator |
| Post-exercise | `write_report_context` → ingest | Persist report, citations, and new findings into the knowledge base |

### `rag_oracle.py` contract

All modes return structured JSON (Pydantic models in `schemas.py`). Every response includes `request_id`, `index_version`, and `embedding_model` for audit reproducibility.

#### Mode 1: `retrieve_context`

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | Natural-language or structured retrieval query |
| `scenario_type` | string | no | e.g. `recon`, `lateral_movement`, `phishing_awareness` |
| `target_profile` | object | no | Arena target metadata (service, OS, tags) |
| `tags` | string[] | no | Filter tags (`playbook`, `finding`, `ioc`, `runbook`) |
| `environment` | enum | yes | `dev` \| `stage` \| `prod` |
| `project` | string | yes | Project / tenant identifier |
| `top_k` | int | no | Default `8`, max `32` |
| `operator_id` | string | yes | For audit logging |

**Output**

| Field | Type | Description |
|---|---|---|
| `chunks` | ChunkResult[] | Ranked chunks with score, source, summary |
| `filters_applied` | object | Echo of scope filters used |
| `total_candidates` | int | Pre-rerank candidate count |

`ChunkResult`: `chunk_id`, `doc_id`, `score`, `source_path`, `doc_type`, `chunk_text` (truncated), `summary`, `tags`, `content_hash`

#### Mode 2: `build_brief`

**Input**: output of `retrieve_context` + optional `scenario_draft` from Ollama Core.

**Output**

| Field | Type | Description |
|---|---|---|
| `briefing` | string | Compact narrative for Orchestrator / operator |
| `relevance_rationale` | string | Why retrieved sources matter |
| `constraints` | string[] | Scope limits, disallowed techniques, environment notes |
| `citations` | Citation[] | Source references with scores |
| `confidence` | float | Aggregate retrieval confidence (0–1) |

#### Mode 3: `write_report_context`

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `run_id` | uuid | yes | Exercise run identifier |
| `operator_id` | string | yes | Operator who approved the run |
| `scenario_id` | string | yes | Approved scenario reference |
| `telemetry_summary` | object | yes | Structured telemetry from Telemetry Agent |
| `findings` | Finding[] | no | New or confirmed findings |
| `remediation_notes` | string[] | no | Suggested remediation actions |

**Output**

| Field | Type | Description |
|---|---|---|
| `report_id` | uuid | Generated report identifier |
| `report_path` | string | Path under `samson/rag/reports/` |
| `citations` | Citation[] | Evidence links embedded in the report |
| `remediation_references` | ChunkResult[] | Retrieved remediation/playbook chunks |
| `timeline` | TimelineEvent[] | Ordered events for the exercise cycle |

Reports are written as Markdown with a JSON sidecar (`reports/<report_id>.json`) for machine consumption.

### Database schema (PostgreSQL + pgvector)

Enable extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### `documents`

| Column | Type | Notes |
|---|---|---|
| `doc_id` | UUID PK | |
| `source_path` | TEXT NOT NULL | Relative path under `samson/rag/docs/` or external URI |
| `doc_type` | TEXT NOT NULL | `markdown`, `json`, `pdf_derived`, `report`, `playbook`, `finding` |
| `project` | TEXT NOT NULL | |
| `environment` | TEXT NOT NULL | `dev`, `stage`, `prod` |
| `tags` | TEXT[] | GIN index |
| `confidence` | REAL | Source trust score (0–1) |
| `content_hash` | TEXT NOT NULL | SHA-256 of normalized full document |
| `index_version` | INT NOT NULL | Incremented on re-index |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

Unique constraint: `(source_path, project, environment, index_version)`.

#### `document_chunks`

| Column | Type | Notes |
|---|---|---|
| `chunk_id` | UUID PK | |
| `doc_id` | UUID FK → documents | ON DELETE CASCADE |
| `chunk_index` | INT NOT NULL | Order within document |
| `chunk_text` | TEXT NOT NULL | |
| `content_hash` | TEXT NOT NULL | SHA-256 of chunk text |
| `token_count` | INT | Approximate token count |
| `created_at` | TIMESTAMPTZ | |

Index: `(doc_id, chunk_index)`.

#### `embeddings`

| Column | Type | Notes |
|---|---|---|
| `embedding_id` | UUID PK | |
| `chunk_id` | UUID FK → document_chunks | UNIQUE |
| `embedding` | vector(N) | Dimension N matches `embedding_dim` |
| `embedding_model` | TEXT NOT NULL | e.g. `nomic-embed-text`, `llama-embed-v1` |
| `embedding_dim` | INT NOT NULL | |
| `created_at` | TIMESTAMPTZ | |

Index: HNSW or IVFFlat on `embedding` (choice deferred to implementation; HNSW preferred for dev scale).

#### `exercise_runs`

| Column | Type | Notes |
|---|---|---|
| `run_id` | UUID PK | |
| `operator_id` | TEXT NOT NULL | |
| `scenario_id` | TEXT NOT NULL | |
| `project` | TEXT NOT NULL | |
| `environment` | TEXT NOT NULL | |
| `status` | TEXT NOT NULL | `draft`, `approved`, `running`, `completed`, `aborted` |
| `approved_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ | |
| `report_id` | UUID | FK to report artifact |
| `metadata` | JSONB | Scenario params, arena target, policy snapshot |

#### `citations`

| Column | Type | Notes |
|---|---|---|
| `citation_id` | UUID PK | |
| `chunk_id` | UUID FK → document_chunks | |
| `report_id` | UUID NOT NULL | Links to exercise report |
| `run_id` | UUID FK → exercise_runs | |
| `score` | REAL | Retrieval relevance at citation time |
| `cited_at` | TIMESTAMPTZ | |

#### `rag_audit_log`

| Column | Type | Notes |
|---|---|---|
| `audit_id` | UUID PK | |
| `request_id` | UUID NOT NULL | Correlates Orchestrator ↔ RAG calls |
| `mode` | TEXT NOT NULL | `retrieve_context`, `build_brief`, `write_report_context` |
| `operator_id` | TEXT | |
| `project` | TEXT NOT NULL | |
| `environment` | TEXT NOT NULL | |
| `query_hash` | TEXT | SHA-256 of input payload (no raw secrets) |
| `chunks_returned` | INT | |
| `index_version` | INT | |
| `embedding_model` | TEXT | |
| `duration_ms` | INT | |
| `created_at` | TIMESTAMPTZ | |

Append-only. No UPDATE or DELETE in application code.

### Embeddings strategy

| Concern | Decision |
|---|---|
| Dev embedding backend | `llama-cli --embedding` or Ollama embedding API against a lightweight model |
| Production | Same model family as dev; model id stored per row |
| Versioning | `index_version` on `documents`; full re-index when model or chunk strategy changes |
| Chunking | Default 512-token windows, 64-token overlap; configurable in `ingest.py` |
| Deduplication | Skip ingest when `content_hash` unchanged for same `(source_path, project, environment)` |

### Guardrails

#### 1. Scope enforcement

- Retrieval queries MUST include `project` and `environment`.
- `retrieve.py` applies mandatory filters: only documents tagged for the current project/environment or marked `global`.
- Documents tagged `offensive-only` or `restricted` require elevated operator role (enforced by Orchestrator before calling RAG).
- Retrieval MUST NOT query external URLs at runtime; only pre-ingested `samson/rag/docs/` content and approved report artifacts.

#### 2. Explainability

- Every scenario draft presented to an operator MUST include a `build_brief` output with at least one citation.
- Reports MUST include `citations` with `chunk_id`, `source_path`, and `score`.
- Ollama Core receives retrieved context as **read-only grounding**; it does not bypass policy validation.

#### 3. Audit trail

- All `rag_oracle.py` invocations write to `rag_audit_log`.
- `request_id` propagates from Orchestrator through RAG, Ollama, Simulation Runner, and Telemetry.
- Report JSON sidecars are immutable after write; corrections create a new `report_id` with `supersedes` reference.

#### 4. Versioning

- `index_version` increments on bulk re-index.
- API responses echo `index_version` and `embedding_model` so reports remain reproducible.
- `samson/rag/index/` holds dev-local cache; Postgres is the source of truth in deployed environments.

#### 5. Execution boundary

RAG Oracle MUST NOT:

- Trigger simulation execution
- Bypass human approval
- Retrieve from non-ingested external sources
- Return exploit payloads or step-by-step attack instructions against non-arena targets

RAG Oracle MAY:

- Retrieve playbooks, prior findings, remediation guides, and exercise reports
- Support scenario **drafting** and **explanation**
- Ingest new telemetry-backed reports after approved runs complete

### Module responsibilities

| Module | Responsibility |
|---|---|
| `search/ingest.py` | Parse docs, chunk, hash, embed, upsert Postgres, bump `index_version` on model change |
| `search/retrieve.py` | Vector similarity + metadata filters + scope enforcement |
| `search/rerank.py` | Cross-encoder or score fusion; produce `summary` per chunk |
| `rag_oracle.py` | Orchestrator API; audit logging; mode orchestration |
| `schemas.py` | Pydantic I/O models, SQL DDL constants, pgvector dimension config |

## Alternatives Considered

### Dedicated vector database (Qdrant, Weaviate, LanceDB)

- **Pros**: Optimized ANN search, simpler scaling for large corpora
- **Cons**: Additional infrastructure; HexStrike already uses LanceDB for unrelated RAG — mixing concerns risks confusion
- **Rejected for v1**: Postgres + pgvector keeps the data model unified with exercise runs and citations

### File-only RAG (no database)

- **Pros**: Fastest dev bootstrap
- **Cons**: No audit trail, no citation integrity, poor multi-tenant filtering
- **Rejected**: Does not meet guardrail requirements

### RAG embedded directly in Ollama prompts without retrieval service

- **Pros**: Minimal code
- **Cons**: No citations, no versioning, no scope filters, no reproducibility
- **Rejected**: Fails explainability and audit requirements

### Autonomous RAG → execution pipeline

- **Pros**: Faster iteration in lab settings
- **Cons**: Violates Samson SBM policy model; unacceptable operational risk
- **Rejected**: Human approval and Scope/Policy Validation remain mandatory gates

## Consequences

### Positive

- Agents and operators gain grounded context from institutional memory
- Exercise reports are citation-backed and suitable for purple-team retrospectives
- Single Postgres store simplifies backups, IR, and compliance review
- Clear API contract enables parallel work on Orchestrator and RAG implementation

### Negative / trade-offs

- pgvector ANN performance may require tuning (HNSW params, connection pooling) at scale
- Embedding model changes force full re-index
- Additional latency on scenario drafting (retrieval + rerank before Ollama)

### Follow-up work (out of scope for this ADR)

1. Implement `samson/rag/` Python modules per this contract
2. Add Alembic or SQL migrations for the schema above
3. Wire `rag_oracle.py` into Samson Orchestrator
4. Add ADR-001 (platform-wide Samson SBM infrastructure) if not yet written
5. Integration tests: ingest → retrieve → brief → report round-trip on a sample document

## References

- Samson SBM platform discussion (2026-07-16): Orchestrator, Target Arena, Ollama Core, guardrails
- HexStrike `mcp_execution_gate` pattern: human-in-the-loop approval before execution
- PostgreSQL pgvector extension: https://github.com/pgvector/pgvector
