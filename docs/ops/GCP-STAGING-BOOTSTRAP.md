# Path B — GCP staging bootstrap (live evidence)

You chose **staging live artifacts**, not demo schemas and not production money.

## What this is / is not

| Is | Is not |
| --- | --- |
| One **staging** GCP project for KMS + SA + IAM evidence | Production / mainnet value path |
| Input to `run-kms-staging-smoke.sh` + `collect_artifacts.sh` live | GLOBAL GO by itself |
| Optional use of project `gen-lang-client-0574318762` **as staging only** | “Банда = prod” |

If you later want real prod: **new project**, billing alerts, stricter org policies — do not promote this staging project silently.

## Prerequisites (on your machine)

- `gcloud` logged in with permission to enable APIs, create KMS + IAM
- Billing enabled on the project
- Repo checked out with PR #50 ops scripts

## Step 0 — Bootstrap

```bash
export GCP_PROJECT_ID=gen-lang-client-0574318762   # staging only
# secp256k1 = Cloud HSM only → must be REGIONAL (not global)
export GCP_LOCATION=europe-west1                   # or us-east1 / us-central1
export CONFIRM_STAGING=YES
# Optional local SA JSON for smoke (do not commit):
export CREATE_SA_KEY=YES

./scripts/ops/gcp-staging-bootstrap.sh
```

**If you already hit** `ALGORITHM_NOT_SUPPORTED_FOR_PROTECTION_LEVEL` / used `GCP_LOCATION=global`:  
pull latest branch and re-run with a **regional** location (script defaults to HSM). The empty keyring in `global` can be ignored.

Creates:

- KMS keyring `hexstrike-staging` + key `rescue-signer` (`EC_SIGN_SECP256K1_SHA256` @ **HSM**)
- SA `hexstrike-signer@...`
- Custom role least-privilege + key IAM binding
- `artifacts/ops/iam-policy-sample.json`
- `artifacts/ops/gcp-staging-bootstrap-<ts>.json`

## Step 1 — Live KMS smoke (§4c)

```bash
# use exports printed by bootstrap
export KMS_PROVIDER=gcp SIGNER_BACKEND=kms
export GCP_KMS_KEY_NAME=projects/.../cryptoKeyVersions/1
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json   # if CREATE_SA_KEY=YES

./scripts/ops/run-kms-staging-smoke.sh
# need: summary.json result=PASS, sign_test=ok
```

## Step 2 — IAM attestation (§4d)

Bootstrap already wrote `artifacts/ops/iam-policy-sample.json`.  
Operator: enable **Cloud Audit Logs** for Cloud KMS (DATA_WRITE) in Console; keep that note in the JSON `notes` field if needed.

## Step 3 — Paging drill (§7)

No Cloud Run required for drill:

```bash
export ALERT_PAGING_ENABLED=true
export ALERT_WEBHOOK_URL=https://hooks.slack.com/services/... 
# or: export ALERT_PAGERDUTY_KEY=...
python3 scripts/ops/paging_drill.py
# after on-call ACK:
export PAGING_DRILL_ACK=true
python3 scripts/ops/paging_drill.py --record-ack
```

## Step 4 — Shadow soak (§8)

```bash
export GO_LIVE_PHASE=shadow
# run hardened bot against staging telemetry (no broadcast)
python3 scripts/ops/shadow_soak_report.py \
  --events artifacts/sandbox/dummy-bot-events.jsonl \
  --hours 24 \
  --out artifacts/ops/shadow-soak-report.json
```

## Step 5 — Live collect + review

```bash
COLLECT_MODE=live ./scripts/ops/collect_artifacts.sh
# want: docs/ops/evidence/verdict.json → global_go_eligible=true
```

Then paste evidence paths for human **GLOBAL GO / NO-GO**.

## Out of scope for this path (later)

- Cloud Run shadow service  
- Prod project split + billing alerts  
- Mainnet canary value  
