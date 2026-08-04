-- Guardrail proxy deployments and human-in-the-loop queue (ADR-004/005 runtime)
CREATE TABLE IF NOT EXISTS guardrail_proxy_deployments (
    deployment_id UUID PRIMARY KEY,
    execution_id UUID NOT NULL REFERENCES adversary_emulation_results(execution_id),
    run_id UUID REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    policy_profile TEXT NOT NULL,
    listen_host TEXT NOT NULL,
    listen_port INT NOT NULL,
    upstream_base_url TEXT NOT NULL,
    config_path TEXT,
    proxy_config JSONB NOT NULL,
    enforcement_config JSONB NOT NULL,
    blocked_ibans TEXT[] DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    destroyed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS guardrail_pending_actions (
    pending_id UUID PRIMARY KEY,
    deployment_id UUID NOT NULL REFERENCES guardrail_proxy_deployments(deployment_id),
    operator_id TEXT NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    status TEXT NOT NULL DEFAULT 'awaiting_operator_review',
    intercepted_ibans TEXT[] DEFAULT '{}',
    request_body_hash TEXT NOT NULL,
    request_path TEXT NOT NULL,
    reason TEXT NOT NULL,
    operator_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_guardrail_pending_status ON guardrail_pending_actions(status);
CREATE INDEX IF NOT EXISTS idx_guardrail_proxy_execution ON guardrail_proxy_deployments(execution_id);
