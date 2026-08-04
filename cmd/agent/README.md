# HexStrike Battle Agent

Autonomous Go agent for orchestrating and analyzing HexStrike sandbox offensive security tests.

## 🎯 Features

- **Autonomous Execution**: Runs all 7 red-team attacks without user interaction
- **Live Analysis**: Parses test results in real-time
- **Battle Report Generation**: Creates detailed JSON reports with vulnerabilities
- **Readiness Scoring**: Calculates 0-100 sandbox readiness score
- **CLI Interface**: Easy-to-use command-line tool
- **CI/CD Integration**: GitHub Actions workflow included

## 📦 Installation

### From Source (macOS/Linux)

```bash
cd hexstrike-ai
cd cmd/agent
bash build.sh
export PATH="$PATH:$(pwd)/../../bin"
```

### Install Globally

```bash
cd cmd/agent
bash install-agent.sh global
```

## 🛡️ Rescue Engine (P1/P2)

`internal/orchestrator/engine.go` runs **before any rescue sign**:

1. `guard.RouteGuard` — balance / rescue value / escalation
2. `entity.EntityGate` — sync.Map bootstrap + Arkham (`ARKHAM_API_KEY`)
3. Funder allowlist — blocks attack #06 (compromised FUNDER)
4. Dedup registry — blocks attack #02/#04
5. `tx.FeeCalculator` — EIP-1559 +20% tip (when not `DryRun`)

```bash
cd cmd/agent && go test ./...
```

Env: `ARKHAM_API_KEY`, `ARKHAM_API_BASE` (optional), `ALLOWED_FUNDERS` (comma-separated, wired at engine init).


### Run Full Battle Suite

```bash
hexstrike-agent battle
```

### Run with Verbose Output

```bash
hexstrike-agent battle -v
```

### Run from Specific Repository

```bash
hexstrike-agent battle -d /path/to/hexstrike-ai
```

## 📊 Output

Agent generates:

1. **Console Output**: Real-time battle progress + final scorecard
2. **JSON Report**: `artifacts/sandbox/battle-report.json`
   - Timestamp
   - All 7 test results
   - Summary statistics
   - Readiness score
   - List of vulnerabilities

## 🎯 Readiness Score Interpretation

| Score | Status | Action |
|-------|--------|--------|
| 70-100 | ✅ Ready for testnet | Deploy to Sepolia |
| 50-69 | ⚠️ Needs hardening | Fix vulnerabilities |
| 0-49 | ❌ Not ready | Review sandbox setup |

## 🔴 Test Results

Agent analyzes each attack and categorizes as:

- **VULN_CONFIRMED**: Vulnerability exploited
- **DEFENDED**: Attack blocked by hardening
- **INCONCLUSIVE**: Test failed or timing issue

## 📝 Example Report

```json
{
  "timestamp": "2025-01-15T10:30:45Z",
  "summary": {
    "total": 7,
    "vuln_confirmed": 4,
    "defended": 2,
    "inconclusive": 1,
    "readiness_score": 62
  },
  "vulnerabilities": [
    "01-baseline-trigger: bot signed on low balance",
    "02-race-duplicate-sign: 3 rescue txs — no dedup"
  ]
}
```

## 🔧 Architecture

```
cmd/agent/
├── main.go         # CLI entry point
├── agent.go        # Core orchestration logic
├── go.mod          # Go module definition
├── build.sh        # Build script
└── install-agent.sh # Installation script
```

### Key Components

- **NewAgent()**: Initialize agent with repo path
- **Run()**: Execute full battle suite
- **verifyPrerequisites()**: Check for required tools
- **runAllTests()**: Execute 7 attacks
- **analyzeResults()**: Parse and categorize outcomes
- **generateReport()**: Create JSON + console output

## 🔄 CI/CD Integration

Agent runs automatically on:
- Every push to `main`/`master`/`develop`
- Every pull request modifying sandbox or agent code
- Results posted as PR comment

Enable in GitHub Actions: `.github/workflows/agent-battle.yml`

## 🎓 Development

### Build Agent

```bash
cd cmd/agent
go build -o ../../bin/hexstrike-agent
```

### Run Locally

```bash
./bin/hexstrike-agent battle -v
```

### Debug

```bash
go run cmd/agent/*.go battle -v -d $(pwd)
```

## 📋 Agent Workflow

```
1. Verify prerequisites (anvil, cast, python3, bash)
   ↓
2. Setup environment (create artifacts dir, run setup-anvil-env.sh)
   ↓
3. Run all 7 attacks sequentially
   ├── 01-baseline-trigger
   ├── 02-race-duplicate-sign
   ├── 03-front-run-drain
   ├── 04-replay-rescue-tx
   ├── 05-toctou-nonce-bump
   ├── 06-compromised-funder
   └── 07-hardening-blocks-tamper
   ↓
4. Parse results from test output
   ↓
5. Analyze vulnerabilities
   ↓
6. Generate report (JSON + console)
   ↓
7. Calculate readiness score (0-100)
   ↓
8. Exit with appropriate status code
```

## 🐛 Troubleshooting

### "anvil not found"
Install Foundry:
```bash
curl -L https://foundry.paradigm.xyz | bash && foundryup
```

### "cast not found"
Rebuild Foundry:
```bash
foundryup
```

### "python3 not found"
Install Python 3.10+:
```bash
# macOS
brew install python3

# Linux
sudo apt install python3
```

### Tests fail with "connection refused"
Agent automatically starts Anvil, but verify:
```bash
lsof -i :8545  # Check if port 8545 in use
```

## 🤝 Contributing

To extend the agent:

1. Add new attack test to `scripts/sandbox/redteam/`
2. Update `runAllTests()` to include new attack
3. Run agent to verify integration
4. Submit PR with test results

## 📄 License

Same as hexstrike-ai

## 🎯 Next Steps

- [ ] Merge PR #21 to master
- [ ] Build agent: `cd cmd/agent && bash build.sh`
- [ ] Run battle: `./bin/hexstrike-agent battle -v`
- [ ] Review `artifacts/sandbox/battle-report.json`
- [ ] Deploy to testnet if score ≥ 70
