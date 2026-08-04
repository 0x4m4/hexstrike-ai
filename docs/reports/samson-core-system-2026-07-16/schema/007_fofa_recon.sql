-- FOFA hybrid OSINT recon (Redis/port hunting) — budget + artifact cache
INSERT INTO api_credit_budgets (
    budget_id, provider, credits_remaining, credits_total, min_interval_sec, is_blocked
) VALUES (
    'fofa_default', 'fofa', 100, 100, 5.0, FALSE
)
ON CONFLICT (budget_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS fofa_recon_artifacts (
    artifact_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    run_id UUID REFERENCES exercise_runs(run_id),
    operator_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    query_text TEXT,
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

CREATE INDEX IF NOT EXISTS idx_fofa_recon_ip
    ON fofa_recon_artifacts (ip_address);
CREATE INDEX IF NOT EXISTS idx_fofa_recon_collected
    ON fofa_recon_artifacts (collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_fofa_recon_ports
    ON fofa_recon_artifacts USING GIN (open_ports);
CREATE INDEX IF NOT EXISTS idx_fofa_recon_cves
    ON fofa_recon_artifacts USING GIN (detected_vulnerabilities);
