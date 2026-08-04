# Go-Live Gate Checklist (HexStrike)

> Decision policy: **FAIL-CLOSED**.  
> If any Critical gate is not PASS → **NO-GO**.

Technical implementation map: [`docs/GO-LIVE-MERGE-GATE-CHECKLIST.md`](GO-LIVE-MERGE-GATE-CHECKLIST.md)  
CI: `.github/workflows/policy-gate.yml` + `.github/workflows/go-live-merge-gate.yml`  
**Final evidence report:** [`docs/ops/FINAL-GO-LIVE-EVIDENCE-REPORT.md`](ops/FINAL-GO-LIVE-EVIDENCE-REPORT.md)  
**Operator steps → GLOBAL GO:** [`docs/ops/GLOBAL-GO-OPERATOR-RUNBOOK.md`](ops/GLOBAL-GO-OPERATOR-RUNBOOK.md)  
Ops packs: [KMS smoke](ops/KMS-STAGING-SMOKE.md) · [KMS IAM](ops/KMS-IAM-HARDENING.md) · [Paging](ops/PAGING-ONCALL.md)

## 0) Scope & Legality (Critical)

- [ ] Tx execution is limited to wallets/keys we are authorized to operate.
- [ ] Third-party wallets are intel/read-only only (no signing/broadcast path).
- [ ] Environment scope is explicitly documented (sandbox vs production-like).

## 1) Compromised Funder/Destination Defense (Critical)

> Implementation: `check_allowlist` + Go `PrepareRescue`; events `BLOCK_COMPROMISED_FUNDER`; empty-list fail-closed via `REQUIRE_ALLOWLIST` / `RequireAllowlist`. Bypass tests in `test_production_gates.py` + `engine_test.go`.

- [ ] `destination_allowlist` enforced in execution path.
- [ ] `funder_allowlist` enforced in execution path.
- [ ] Negative tests prove non-allowlisted destination/funder is blocked.
- [ ] Guard event emits `BLOCK_COMPROMISED_FUNDER` (or equivalent) on deny.

## 2) TOCTOU Controls (Critical)

- [ ] `intent_hash = H(chainId,to,value,data,nonce,policyVersion)` computed before sign.
- [ ] Nonce reservation/lock enabled (no concurrent nonce race).
- [ ] Single-flight mutex enabled per wallet/executor.
- [ ] Post-sign, pre-broadcast direct/quorum recheck (balance + nonce + intent parity).
- [ ] Mismatch/drift triggers hard drop + critical alert.

## 3) Replay Resistance (Critical)

- [ ] Broadcast dedup by `(intent_hash, nonce, chainId)`.
- [ ] Re-submit with mutated intent is rejected.
- [ ] Cross-chain replay prevented by chain binding.

## 4) Key Management (Critical)

- [ ] No raw private keys in app env/CI.
- [ ] Signing uses KMS/HSM/remote signer only.
- [ ] Signer access is policy-scoped + auditable.

**Code wiring (real cloud SDKs — not interface-only):**
- `SIGNER_BACKEND=kms` → `signer.NewFromEnv` → AWS SDK v2 (`AWS_KMS_KEY_ID`, `AWS_REGION`) or GCP Cloud KMS (`KMS_PROVIDER=gcp`, `GCP_KMS_KEY_NAME`).
- Implementations: `cmd/agent/internal/signer/kms_aws.go`, `kms_gcp.go`, `eth_sig.go` (DER→eth `[R||S||V]`).
- Fail-closed without cloud config; `local_key` rejected outside `GO_LIVE_PHASE=lab`.
- Optional bind check: `SIGNER_ADDRESS` must match address derived from KMS public key.
- Live cloud credentials are operator-owned; unit tests mock SDK clients (`kms_*_test.go`).
- Staging smoke: `scripts/ops/run-kms-staging-smoke.sh` → `artifacts/ops/kms-smoke-*/summary.json` ([runbook](ops/KMS-STAGING-SMOKE.md)).
- IAM templates: `docs/ops/iam/` + [KMS-IAM-HARDENING.md](ops/KMS-IAM-HARDENING.md).

## 5) RPC Trust Model (Critical)

- [ ] Multi-RPC configured (>=3 providers recommended).
- [ ] Quorum validation enabled (2/3 minimum) for critical reads.
- [ ] Single-provider disagreement results in fail-closed behavior.

## 6) Transaction Risk Limits (Critical)

- [ ] Per-tx value cap enabled.
- [ ] Per-window/day cap enabled.
- [ ] Cooldown enabled after risk events.
- [ ] Emergency kill switch tested and operational.

## 7) Detection & Response (High)

- [ ] Critical alerts route to paging/on-call (not jsonl-only).
- [ ] Runbook exists for block/rollback/recovery.
- [ ] At least one incident drill executed successfully.

Wiring: `ALERT_PAGING_ENABLED` + `ALERT_WEBHOOK_URL` → Python `alert_paging.py` / Go `alerting.PageCritical`.  
Drill: `python3 scripts/ops/paging_drill.py` → [PAGING-ONCALL.md](ops/PAGING-ONCALL.md).

## 8) Rollout Phases (Critical)

### Phase A — Shadow (no sign, no broadcast)

- [ ] Guard decisions stable on real telemetry.

### Phase B — Dry-sign (sign only, no broadcast)

- [ ] Signer integration stable, audit logs complete.

### Phase C — Canary Live (tiny value)

- [ ] Limited to allowlisted destination(s).
- [ ] Strict tiny budget + short observation window.
- [ ] Any critical alert auto-disables broadcast.

### Phase D — Limited Production

- [ ] Limits increased gradually with explicit approvals.
- [ ] No critical policy violations during canary window.

---

## Final Decision

- **GO** only if all Critical items PASS.
- Otherwise **NO-GO** and open remediation issues.
