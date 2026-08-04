-- Samson SBM unified schema (ADR-002 through ADR-005)
CREATE EXTENSION IF NOT EXISTS vector;

-- ADR-002 RAG
CREATE TABLE IF NOT EXISTS documents (
    doc_id UUID PRIMARY KEY,
    source_path TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    project TEXT NOT NULL,
    environment TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    confidence REAL DEFAULT 1.0,
    content_hash TEXT NOT NULL,
    index_version INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_path, project, environment, index_version)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id UUID PRIMARY KEY,
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    token_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (doc_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id UUID PRIMARY KEY,
    chunk_id UUID NOT NULL UNIQUE REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
    embedding vector(768),
    embedding_model TEXT NOT NULL,
    embedding_dim INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS exercise_runs (
    run_id UUID PRIMARY KEY,
    operator_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    project TEXT NOT NULL,
    environment TEXT NOT NULL,
    status TEXT NOT NULL,
    approved_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    report_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS citations (
    citation_id UUID PRIMARY KEY,
    chunk_id UUID NOT NULL REFERENCES document_chunks(chunk_id),
    report_id UUID NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    score REAL,
    cited_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_audit_log (
    audit_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    mode TEXT NOT NULL,
    operator_id TEXT,
    project TEXT NOT NULL,
    environment TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    chunks_returned INT,
    index_version INT,
    embedding_model TEXT,
    duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ADR-003 Red team tools
CREATE TABLE IF NOT EXISTS redteam_scans (
    scan_id UUID PRIMARY KEY,
    tool TEXT NOT NULL,
    request_id UUID NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    model_name TEXT,
    scenario_id TEXT,
    risk_score REAL,
    risk_band TEXT,
    hit_rate REAL,
    report_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS atlas_mappings (
    mapping_id UUID PRIMARY KEY,
    run_id UUID REFERENCES exercise_runs(run_id),
    atlas_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    confidence REAL,
    evidence TEXT,
    taxonomy_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS redteam_audit_log (
    audit_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    tool TEXT NOT NULL,
    operator_id TEXT,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    duration_ms INT,
    run_id UUID REFERENCES exercise_runs(run_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ADR-004 Impact / remediation
CREATE TABLE IF NOT EXISTS impact_simulations (
    simulation_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    simulation_profile TEXT NOT NULL,
    phases_executed TEXT[] DEFAULT '{}',
    synthetic_artifacts TEXT[] DEFAULT '{}',
    atlas_technique_ids TEXT[] DEFAULT '{}',
    reversible BOOLEAN DEFAULT TRUE,
    restored_at TIMESTAMPTZ,
    audit_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS remediation_demos (
    demo_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES exercise_runs(run_id),
    simulation_id UUID REFERENCES impact_simulations(simulation_id),
    demo_type TEXT NOT NULL,
    report_id UUID,
    audience TEXT NOT NULL,
    pyrit_post_score REAL,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS guardrail_deployments (
    deployment_id UUID PRIMARY KEY,
    demo_id UUID REFERENCES remediation_demos(demo_id),
    arena_namespace TEXT NOT NULL,
    policy_rules JSONB NOT NULL,
    status TEXT NOT NULL,
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    destroyed_at TIMESTAMPTZ
);

-- ADR-005 Financial
CREATE TABLE IF NOT EXISTS financial_simulations (
    simulation_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    technique TEXT NOT NULL,
    mock_merchant_id TEXT,
    synthetic_amount_eur REAL,
    substitution_success BOOLEAN,
    guardrail_active BOOLEAN DEFAULT FALSE,
    atlas_technique_ids TEXT[] DEFAULT '{}',
    ledger_snapshot_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS financial_guardrail_deployments (
    deployment_id UUID PRIMARY KEY,
    simulation_id UUID REFERENCES financial_simulations(simulation_id),
    policy_profile TEXT NOT NULL,
    rules_applied JSONB NOT NULL,
    pre_block_events INT DEFAULT 0,
    post_block_events INT DEFAULT 0,
    status TEXT NOT NULL,
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    destroyed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS synthetic_ledger (
    entry_id UUID PRIMARY KEY,
    simulation_id UUID REFERENCES financial_simulations(simulation_id),
    merchant_id TEXT,
    iban_from TEXT,
    iban_to TEXT,
    amount_eur REAL,
    status TEXT,
    synthetic BOOLEAN NOT NULL DEFAULT TRUE CHECK (synthetic = TRUE),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
