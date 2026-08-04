# GO-LIVE Merge Gate Checklist (technical map)

Operator decision checklist (canonical): [`docs/GO_LIVE_CHECKLIST.md`](GO_LIVE_CHECKLIST.md)  
PR template: `.github/pull_request_template.md` · CI: `policy-gate.yml` + this file

Use this technical map for implementation verification before enabling any non-lab money path.
**If any Phase 0 item is unchecked → NO-GO.**

## Phase 0 — Pre-Go (mandatory)

| ID | Gate | Requirement | Verify |
| --- | --- | --- | --- |
| P0-06 | G-Allowlist | `ALLOWED_FUNDERS` + `ALLOWED_DESTINATIONS`; unsigned if `to` ∉ allowlist | `go test ./cmd/agent/internal/orchestrator/... -run CompromisedFunder` + `python3 scripts/sandbox/test_production_gates.py` |
| P0-TOCTOU | G-TOCTOU | Intent hash `{to,value,data,chainId,nonce}` before sign; nonce lock; post-sign recheck; dedup `intent_hash+nonce` | `go test ./cmd/agent/internal/guard/...` + production gate tests |
| P0-SIGNER | Signer isolation | KMS/HSM in staging/prod; raw key forbidden outside lab | `SIGNER_BACKEND=kms` + no `BOT_PRIVATE_KEY` in CI/prod env |
| P0-RPC | G-RPC | ≥3 RPC endpoints; proceed only on **2/3** quorum for balance/nonce | `QUORUM_RPC_URLS` + `QUORUM_MIN_AGREE=2` |
| P0-LIMITS | Rate / budget | `MAX_RESCUES_PER_WINDOW`, cooldown after block, phase caps (`CANARY_MAX_VALUE_WEI`) | production_gates `TxRateLimiter` tests |
| P0-KILL | Kill switch | `KILL_SWITCH=true` halts all signing fail-closed | `guard.KillSwitch` tests |
| P0-OPS | Paging | Critical alerts → on-call sink (not jsonl-only) | runbook wired in staging |

## Phase 1 — Shadow (read-only)

| ID | Requirement | Verify |
| --- | --- | --- |
| P1-SHADOW | `GO_LIVE_PHASE=shadow` — RPC/telemetry only, **no sign/broadcast** | `check_signer_policy` → `shadow_mode_no_sign` |
| P1-ALERTS | Guard decisions + alerts on real RPC data | shadow soak ≥24h, zero signed txs |

## Phase 2 — Canary (tiny value)

| ID | Requirement | Verify |
| --- | --- | --- |
| P2-CANARY | `GO_LIVE_PHASE=canary`; value ≤ `CANARY_MAX_VALUE_WEI` | cap enforced in `sign_rescue_tx_gated` |
| P2-AUTO-STOP | Any critical alert → kill switch / auto-stop | runbook drill |

## Phase 3 — Limited production

| ID | Requirement | Verify |
| --- | --- | --- |
| P3-LIMITED | Gradual limit increase; all fail-closed guardrails remain | change ticket + dual approval |
| P3-NO-BYPASS | No path signs without G1→G2→G3 + TOCTOU | battle + code review |

---

## Transaction rules (mandatory)

```text
trigger → G1 → G2 → G3 → (Phase 0 gates) → fix intent hash → sign → post-sign recheck → broadcast
```

| Step | Rule |
| --- | --- |
| Pre-sign | Bind `intent_hash` to `{to,value,data,chainId,nonce}` |
| Post-sign | Quorum recheck `balance+nonce`; drift ⇒ drop tx + critical alert |
| Dedup | Reject duplicate `intent_hash+nonce` |
| Fail-closed | Direct/quorum RPC unavailable ⇒ no broadcast |

---

## CI commands (local / PR)

```bash
# Go unit gates
cd cmd/agent && go test ./...

# Python Phase 0 gates
python3 scripts/sandbox/test_production_gates.py
python3 scripts/sandbox/test_attack_blocked.py

# Sandbox battle (Anvil only)
./bin/hexstrike-agent battle -v

# Hardened attack #06
bash scripts/sandbox/redteam/06-compromised-funder-hardened.sh
```

---

## Readiness matrix

| Environment | Required gates |
| --- | --- |
| Lab / Anvil | G-Lab, battle suite |
| Staging | Phase 0 + Phase 1 shadow |
| Canary | Phase 0 + Phase 2 |
| Production | **All** Phase 0–3 + G-Score ≥ 70 + `06` DEFENDED |

---

## PR template snippet

```markdown
### GO-LIVE merge gate

- [ ] P0-06 Allowlist tests PASS
- [ ] P0-TOCTOU intent hash + post-sign recheck implemented
- [ ] P0-SIGNER KMS/HSM (no raw key in prod CI)
- [ ] P0-RPC quorum 2/3 configured
- [ ] P0-LIMITS + kill switch tested
- [ ] P0-OPS paging connected
- [ ] Phase documented (shadow / canary / limited)
- [ ] No mainnet withdrawal without explicit operator GO
```
