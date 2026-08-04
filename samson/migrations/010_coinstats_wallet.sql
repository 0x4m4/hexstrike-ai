-- CoinStats public wallet OSINT snapshots (read-only balances / txs)
CREATE TABLE IF NOT EXISTS coinstats_wallet_artifacts (
    artifact_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    address TEXT NOT NULL,
    connection_id TEXT NOT NULL,
    is_empty BOOLEAN NOT NULL DEFAULT TRUE,
    token_count INTEGER NOT NULL DEFAULT 0,
    total_value_usd NUMERIC NOT NULL DEFAULT 0,
    transactions_synced BOOLEAN NOT NULL DEFAULT FALSE,
    transaction_count INTEGER NOT NULL DEFAULT 0,
    from_cache BOOLEAN NOT NULL DEFAULT FALSE,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coinstats_wallet_address
    ON coinstats_wallet_artifacts (LOWER(address), connection_id);
CREATE INDEX IF NOT EXISTS idx_coinstats_wallet_collected
    ON coinstats_wallet_artifacts (collected_at DESC);
