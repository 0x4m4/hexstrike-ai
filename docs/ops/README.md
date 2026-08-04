# Ops packs — close operator-owned go-live blockers

| Pack | Doc | Script |
| --- | --- | --- |
| **Step-by-step → GLOBAL GO** | [GLOBAL-GO-OPERATOR-RUNBOOK.md](GLOBAL-GO-OPERATOR-RUNBOOK.md) | steps 0–5 |
| **Path B: GCP staging bootstrap** | [GCP-STAGING-BOOTSTRAP.md](GCP-STAGING-BOOTSTRAP.md) | `gcp-staging-bootstrap.sh` |
| **Collect + validate evidence** | [evidence/](evidence/) | `collect_artifacts.sh` + `validate_schemas.py` |
| Staging KMS smoke | [KMS-STAGING-SMOKE.md](KMS-STAGING-SMOKE.md) | `scripts/ops/run-kms-staging-smoke.sh` |
| IAM least privilege | [KMS-IAM-HARDENING.md](KMS-IAM-HARDENING.md) | `docs/ops/iam/*` |
| Paging / on-call | [PAGING-ONCALL.md](PAGING-ONCALL.md) | `scripts/ops/paging_drill.py` |
| Shadow soak report | runbook §4 | `scripts/ops/shadow_soak_report.py` |
| **Final evidence** | [FINAL-GO-LIVE-EVIDENCE-REPORT.md](FINAL-GO-LIVE-EVIDENCE-REPORT.md) | fill → GLOBAL GO/NO-GO |

Canonical checklist: [`docs/GO_LIVE_CHECKLIST.md`](../GO_LIVE_CHECKLIST.md).
