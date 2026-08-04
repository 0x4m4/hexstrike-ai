# Paste-ready update for PR #46

Copy everything below the line into the PR description (replace or append).

---

## Phase 0 GO-LIVE gates + merge policy

Fail-closed money-circuit controls + operator checklist / CI policy gate. **No mainnet withdrawal enablement.**

### Go-Live Gates Introduced

Commit: `3a72479`

| File | Role |
| --- | --- |
| `docs/GO_LIVE_CHECKLIST.md` | Canonical fail-closed operator checklist (Critical → NO-GO) |
| `.github/pull_request_template.md` | PR Critical Gates checklist for every change |
| `.github/workflows/policy-gate.yml` | CI policy gate on `main`/`master` (`push` + `pull_request`) |

**Required review before merge (please approve these files):**
- [ ] `docs/GO_LIVE_CHECKLIST.md`
- [ ] `.github/workflows/policy-gate.yml`

### Implementation
- Allowlist (#06) + `BLOCK_COMPROMISED_FUNDER` alert/event
- TOCTOU: `intent_hash = H(chainId,to,value,data,nonce,policyVersion)`, nonce lock, post-sign recheck, dedup
- Quorum 2/3, rate limits, kill switch, shadow/canary phases
- CI: `go-live-merge-gate.yml` + `policy-gate.yml`

### Also on this PR (prior)
- CoinStats wallet OSINT (`coinstats-wallet`) — read-only
- ARCHITECTURE defense-in-depth, SMS-2FA threat model, sweeper/drainer purple-team, Arkham/FOFA recon

### Tests / CI evidence
- `go test ./internal/guard/... ./internal/orchestrator/...` — PASS
- `python3 scripts/sandbox/test_production_gates.py` — PASS
- `policy-gate` / job `gate` on this PR — SUCCESS
- `GO-LIVE Merge Gate` / `phase0-gates` — SUCCESS

### Risk posture
- Fail-closed: any Critical gate missing → **NO-GO**
- Step 3 hardening remains **risk-reduced**, not production-complete
- Raw keys must never land in tracked env/CI

### Why this is a NO-GO / GO framework
- **NO-GO** until all Critical items in `GO_LIVE_CHECKLIST.md` PASS (KMS/HSM + paging still operator-owned)
- **GO** only after Shadow → Dry-sign → Canary → Limited phases with explicit approvals
- After merge: enable branch protection on `master` with required status check = `policy-gate` (check name: `gate`)
