## PR Review — Sandbox Steps 1–3

### Summary
Solid incremental sandbox for defensive RPC/bot research. Steps are well separated: baseline bot → logging proxy → hardening guards. No offensive falsification code — appropriate scope.

### What looks good
- Clear step runners (`run-step1/2/3-defensive.sh`)
- `balance_guard.py` multi-source check + pre-sign verify is the right defensive pattern
- JSONL artifacts for audit trail
- Interceptor remains pass-through (Step 2)

### Required before merge
- [x] `anvil.env` gitignored; example uses placeholders
- [x] `setup-anvil-env.sh` generates local env with Anvil public keys
- [x] Sandbox README with run instructions

### Suggestions (non-blocking)
- [ ] CI smoke: Anvil + `dummy_bot.py --once --dry-run` in GitHub Actions
- [ ] Consider pinning Foundry version in CI for reproducibility
- [ ] Future: unit tests for `balance_guard.detect_rpc_mismatch()` with mocked RPC

### Security
- Confirm no real private keys in committed files — `anvil.env.example` should stay placeholder-only ✅
- Document that hardening protects against proxy tampering but is not a production wallet solution

### Verdict
**Approve** after verifying Mac smoke test:
```bash
./scripts/sandbox/run-step1.sh   # Ctrl+C after one poll
./scripts/sandbox/run-step3-defensive.sh
./scripts/sandbox/set-balance.sh $BOT_ADDRESS 300000000000000000
```

Expected: bot events + (Step 3) signed rescue when both RPC sources agree on low balance.
