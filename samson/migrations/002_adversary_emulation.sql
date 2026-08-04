-- Adversary emulation results with pgvector response embeddings (schemas contract)
CREATE TABLE IF NOT EXISTS adversary_emulation_results (
    execution_id UUID PRIMARY KEY,
    target_id UUID NOT NULL,
    payload_id UUID NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    request_id UUID,
    operator_id TEXT NOT NULL,
    attack_vector TEXT NOT NULL,
    interface_type TEXT NOT NULL,
    http_status_code INT NOT NULL,
    vulnerability_verified BOOLEAN NOT NULL,
    response_payload JSONB NOT NULL,
    intercepted_financial_entities TEXT[] DEFAULT '{}',
    response_embedding vector(768),
    rag_document_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_adversary_emulation_run ON adversary_emulation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_adversary_emulation_operator ON adversary_emulation_results(operator_id);
CREATE INDEX IF NOT EXISTS idx_adversary_emulation_embedding ON adversary_emulation_results
    USING hnsw (response_embedding vector_cosine_ops);
