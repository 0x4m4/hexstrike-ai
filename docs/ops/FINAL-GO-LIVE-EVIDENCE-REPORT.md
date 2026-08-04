# Final Go-Live Evidence Report

| Field | Value |
| --- | --- |
| Document | `docs/ops/FINAL-GO-LIVE-EVIDENCE-REPORT.md` |
| Operator runbook | [`GLOBAL-GO-OPERATOR-RUNBOOK.md`](GLOBAL-GO-OPERATOR-RUNBOOK.md) |
| Checklist | `docs/GO_LIVE_CHECKLIST.md` |
| Docs consistency | **GO** (`cursor/samson-production-core-f2e6` @ `edfb3e0`) |
| Reviewed at (UTC) | 2026-07-17 |
| Reviewer | Operator + agent formalization |
| **STAGING VERDICT** | **GO** — see [`STAGING-GO-VERDICT.md`](STAGING-GO-VERDICT.md) |
| **PRODUCTION GLOBAL VERDICT** | **NO-GO** until all Critical operator artifact rows = PASS |

Policy: **FAIL-CLOSED**. Staging GO ≠ Production GLOBAL GO.

---

## Operator artifact matrix (required for GLOBAL GO)

| Критерий | Артефакт | Статус |
|----------|----------|--------|
| §4c Live KMS smoke | `artifacts/ops/kms-smoke-*/summary.json` (`result=PASS`, `sign_test=ok`, `fail_closed_test=ok`) | **PENDING** |
| §4d IAM/audit | `artifacts/ops/iam-policy-sample.json` (+ CloudTrail/Audit note) | **PENDING** |
| §7 Paging drill | `artifacts/ops/paging-drill-*.json` (`result=PASS`, `alert_sent`, `webhook_status`, `ack_received`) | **PENDING** |
| §8 Shadow soak | `artifacts/ops/shadow-soak-report.json` | **PENDING** |
| §8 Canary | canary logs / tx hashes + no critical alerts | **PENDING** |
| §0 Scope & legality | authorized-wallet scope doc | **PENDING** |

---

## Code-side Critical (pre-filled — not sufficient alone)

| § | Gate | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Allowlist #06 | **GO** (code) | PR #48/#49; DEFENDED* in ARCHITECTURE |
| 2 | TOCTOU SecureSignRescue | **GO** (code) | `secure_sign.go` + tests |
| 3 | Replay | **GO** (code) | intent claim `(intent_hash, nonce, chainId)` |
| 4b | KMS AWS/GCP SDK | **GO** (code) | `kms_aws.go` / `kms_gcp.go` |
| 4a | No raw keys in CI | **GO** (CI) | `policy-gate.yml` / PR #47 |
| 5 | Quorum fail-closed | **GO** (code) | Engine + `production_gates.py` |
| 6 | Limits / kill switch | **GO** (code) | Engine `OnCritical` |
| Docs | ARCHITECTURE consistency | **GO** | `edfb3e0` on samson-production-core |

---

## How to close PENDING rows

1. Follow [`GLOBAL-GO-OPERATOR-RUNBOOK.md`](GLOBAL-GO-OPERATOR-RUNBOOK.md) steps 1–4 (real KMS/IAM/paging/shadow).  
2. Run **`./scripts/ops/collect_artifacts.sh`** (`COLLECT_MODE=live`) → `docs/ops/evidence/*.json` + `verdict.json` with `global_go_eligible=true`.  
3. `COLLECT_MODE=demo` is schema CI only — **never** GLOBAL GO.  
4. Paste evidence paths for human **GLOBAL GO / NO-GO**.

---

## Sign-off

| Role | Name | Date | Verdict |
| --- | --- | --- | --- |
| Engineering | | | |
| Security / IR | | | |
| On-call owner | | | |

**GLOBAL:** NO-GO until every operator artifact row is PASS.
