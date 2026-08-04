-- Synthetic local-blockchain validation rows (validation_node / LocalBlockchainSandbox)
ALTER TABLE adversary_emulation_results
    ADD COLUMN IF NOT EXISTS synthetic BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_adversary_emulation_synthetic
    ON adversary_emulation_results (synthetic)
    WHERE synthetic = TRUE;
