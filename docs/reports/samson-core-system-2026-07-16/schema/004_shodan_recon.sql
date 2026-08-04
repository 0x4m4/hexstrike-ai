-- Shodan recon artifacts + API credit budget (OSINT recon agent)
CREATE TABLE IF NOT EXISTS api_credit_budgets (
    budget_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    credits_remaining INT NOT NULL CHECK (credits_remaining >= 0),
    credits_total INT NOT NULL CHECK (credits_total >= 0),
    min_interval_sec DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    last_query_at TIMESTAMPTZ,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO api_credit_budgets (
    budget_id, provider, credits_remaining, credits_total, min_interval_sec, is_blocked
) VALUES (
    'shodan_default', 'shodan', 77, 77, 5.0, FALSE
)
ON CONFLICT (budget_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS shodan_recon_artifacts (
    artifact_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    hostnames TEXT[] NOT NULL DEFAULT '{}',
    org TEXT,
    isp TEXT,
    asn TEXT,
    os TEXT,
    country_code TEXT,
    city TEXT,
    open_ports INT[] NOT NULL DEFAULT '{}',
    banners JSONB NOT NULL DEFAULT '[]'::jsonb,
    detected_vulnerabilities TEXT[] NOT NULL DEFAULT '{}',
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    rag_doc_path TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shodan_recon_ip ON shodan_recon_artifacts(ip_address);
CREATE INDEX IF NOT EXISTS idx_shodan_recon_cves ON shodan_recon_artifacts USING GIN (detected_vulnerabilities);
CREATE INDEX IF NOT EXISTS idx_shodan_recon_collected ON shodan_recon_artifacts(collected_at DESC);
