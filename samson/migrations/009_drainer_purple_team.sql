-- Multi-family drainer purple-team suite (EVM ERC20 / USDT / TRX IOC)
CREATE TABLE IF NOT EXISTS drainer_purple_team_runs (
    run_artifact_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    exercise_run_id UUID REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    families_run TEXT[] NOT NULL DEFAULT '{}',
    assertion_passed BOOLEAN NOT NULL DEFAULT FALSE,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drainer_purple_created
    ON drainer_purple_team_runs (created_at DESC);
