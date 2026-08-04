-- Purple-team sweeper emulation runs (synthetic Anvil attack + defense detection)
CREATE TABLE IF NOT EXISTS sweeper_purple_team_runs (
    run_artifact_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    exercise_run_id UUID REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    watched_wallet TEXT NOT NULL,
    destination_wallet TEXT NOT NULL,
    attack_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    attack_swept BOOLEAN NOT NULL DEFAULT FALSE,
    attack_tx_hash TEXT,
    swept_wei NUMERIC NOT NULL DEFAULT 0,
    defense_detected BOOLEAN NOT NULL DEFAULT FALSE,
    defense_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    risk_level TEXT NOT NULL DEFAULT 'unknown',
    indicators TEXT[] NOT NULL DEFAULT '{}',
    assertion_passed BOOLEAN NOT NULL DEFAULT FALSE,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sweeper_purple_dest
    ON sweeper_purple_team_runs (LOWER(destination_wallet));
CREATE INDEX IF NOT EXISTS idx_sweeper_purple_created
    ON sweeper_purple_team_runs (created_at DESC);
