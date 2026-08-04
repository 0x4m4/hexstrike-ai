-- Arkham Intelligence on-chain address recon (defensive OSINT)
-- arkham_recon_artifacts: raw collector cache
-- web3_recon_artifacts: bulk-audit enrichment with risk classification

CREATE TABLE IF NOT EXISTS arkham_recon_artifacts (
    artifact_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    address TEXT NOT NULL,
    chain TEXT,
    entity_name TEXT,
    entity_id TEXT,
    entity_type TEXT,
    label_name TEXT,
    is_contract BOOLEAN,
    is_user_address BOOLEAN,
    chains_seen TEXT[] NOT NULL DEFAULT '{}',
    labels TEXT[] NOT NULL DEFAULT '{}',
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    rag_doc_path TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_arkham_recon_address
    ON arkham_recon_artifacts (LOWER(address));
CREATE INDEX IF NOT EXISTS idx_arkham_recon_entity
    ON arkham_recon_artifacts (entity_id)
    WHERE entity_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_arkham_recon_collected
    ON arkham_recon_artifacts (collected_at DESC);

CREATE TABLE IF NOT EXISTS web3_recon_artifacts (
    artifact_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    address TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'unknown',
    is_risk BOOLEAN NOT NULL DEFAULT FALSE,
    entity_name TEXT,
    entity_id TEXT,
    entity_type TEXT,
    label_name TEXT,
    chains_seen TEXT[] NOT NULL DEFAULT '{}',
    labels TEXT[] NOT NULL DEFAULT '{}',
    from_cache BOOLEAN NOT NULL DEFAULT FALSE,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    rag_doc_path TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web3_recon_address
    ON web3_recon_artifacts (LOWER(address));
CREATE INDEX IF NOT EXISTS idx_web3_recon_risk
    ON web3_recon_artifacts (is_risk)
    WHERE is_risk = TRUE;
CREATE INDEX IF NOT EXISTS idx_web3_recon_collected
    ON web3_recon_artifacts (collected_at DESC);
