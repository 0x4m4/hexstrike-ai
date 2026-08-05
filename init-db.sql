-- Create tables for storing scan results
CREATE TABLE IF NOT EXISTS scan_results (
    id SERIAL PRIMARY KEY,
    scan_type VARCHAR(50) NOT NULL,
    target VARCHAR(255) NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20),
    results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vulnerabilities (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER REFERENCES scan_results(id),
    severity VARCHAR(20),
    title VARCHAR(255),
    description TEXT,
    cve_id VARCHAR(50),
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scan_results_target ON scan_results(target);
CREATE INDEX idx_vulnerabilities_severity ON vulnerabilities(severity);
```

---

## Step 7: Create .dockerignore

`.dockerignore`:
```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
hexstrike-env/
.git
.gitignore
*.log
.vscode
.idea
results/
logs/
*.swp
.DS_Store
docker-compose.override.yml