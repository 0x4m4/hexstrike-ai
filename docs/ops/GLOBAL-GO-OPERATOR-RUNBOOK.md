# Operator runbook → GLOBAL GO

Fail-closed: any Critical cell without artifact → **GLOBAL NO-GO**.  
When all artifacts exist, paste paths into chat for final GO/NO-GO.

Canonical evidence matrix: [`FINAL-GO-LIVE-EVIDENCE-REPORT.md`](FINAL-GO-LIVE-EVIDENCE-REPORT.md).

**Path B (chosen): GCP staging live evidence** — start here:  
[`GCP-STAGING-BOOTSTRAP.md`](GCP-STAGING-BOOTSTRAP.md) → `scripts/ops/gcp-staging-bootstrap.sh`  
(Staging only — not production. Demo schemas = Path A, not this path.)

---

## Шаг 0 — GCP staging bootstrap (Path B)

```bash
export GCP_PROJECT_ID=<staging-project>   # e.g. gen-lang-client-0574318762 as STAGING only
export GCP_LOCATION=europe-west1          # regional — secp256k1 needs Cloud HSM (not global)
export CONFIRM_STAGING=YES
export CREATE_SA_KEY=YES                  # optional local SA JSON — never commit
./scripts/ops/gcp-staging-bootstrap.sh
```

---

## Шаг 1 — Live KMS smoke (§4c)

### AWS

```bash
# 1. AWS Console → Customer managed keys → Asymmetric → ECC_SECG_P256K1 → Sign/verify
# 2. KeyId (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) or full ARN
export AWS_KMS_KEY_ID=<key-id-or-arn>
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=<...>
export AWS_SECRET_ACCESS_KEY=<...>
# Prefer task role / instance profile in staging over long-lived keys.
export SIGNER_BACKEND=kms
export KMS_PROVIDER=aws
# Optional bind:
# export SIGNER_ADDRESS=0x...

./scripts/ops/run-kms-staging-smoke.sh
# → artifacts/ops/kms-smoke-<timestamp>/summary.json
```

### GCP

```bash
export GCP_KMS_KEY_NAME=projects/<proj>/locations/<loc>/keyRings/<ring>/cryptoKeys/<key>/cryptoKeyVersions/1
export SIGNER_BACKEND=kms
export KMS_PROVIDER=gcp
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

./scripts/ops/run-kms-staging-smoke.sh
```

**Required `summary.json` shape (PASS):**

```json
{
  "result": "PASS",
  "provider": "aws",
  "sign_test": "ok",
  "fail_closed_test": "ok"
}
```

`PASS_WITH_OPERATOR_SKIP` / `sign_test: skip` = **not** sufficient for §4c GO.

---

## Шаг 2 — IAM hardening (§4d)

### AWS

Prefer least-privilege template: [`iam/aws-kms-signer-policy.json`](iam/aws-kms-signer-policy.json)  
(Console key-policy sketch — bind **bot role only**, scope Resource to the key ARN, not `*`:)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::<account>:role/<bot-role>" },
    "Action": ["kms:Sign", "kms:GetPublicKey"],
    "Resource": "arn:aws:kms:<region>:<account>:key/<key-id>"
  }]
}
```

1. Apply via KMS → Key policy.  
2. Remove extra principals (`*`, unnecessary root/human admins — use break-glass).  
3. Enable CloudTrail data events for KMS.  
4. Export redacted policy → `artifacts/ops/iam-policy-sample.json`.

### GCP

1. SA with signer permissions **only on that key** (custom role in [`iam/gcp-kms-signer-role.yaml`](iam/gcp-kms-signer-role.yaml); avoid broad `roles/owner` / `editor`).  
2. Enable Cloud Audit Logs for Cloud KMS.  
3. Save binding export → `artifacts/ops/iam-policy-sample.json`.

Details: [`KMS-IAM-HARDENING.md`](KMS-IAM-HARDENING.md).

---

## Шаг 3 — Paging drill (§7)

```bash
export ALERT_PAGING_ENABLED=true
# Slack (or any HTTPS webhook):
export ALERT_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
# OR PagerDuty Events API v2:
# export ALERT_PAGERDUTY_KEY=<integration-key>

python3 scripts/ops/paging_drill.py
# After on-call ACKs the page in Slack/PD:
export PAGING_DRILL_ACK=true
python3 scripts/ops/paging_drill.py --record-ack
```

**Required `paging-drill-*.json` shape (PASS):**

```json
{
  "result": "PASS",
  "alert_sent": true,
  "webhook_status": 200,
  "ack_received": true
}
```

---

## Шаг 4 — Shadow / Canary evidence (§0 / §8)

```bash
# Shadow — no sign / no broadcast
export GO_LIVE_PHASE=shadow
# Run hardened bot against staging telemetry; confirm zero broadcast TX
# Events → artifacts/sandbox/dummy-bot-events.jsonl

# After soak window, generate report:
python3 scripts/ops/shadow_soak_report.py \
  --events artifacts/sandbox/dummy-bot-events.jsonl \
  --hours 24 \
  --out artifacts/ops/shadow-soak-report.json

# Canary — tiny value only (example 0.1 ETH; prefer smaller)
export GO_LIVE_PHASE=canary
export CANARY_MAX_VALUE_WEI=100000000000000000
# Attach canary tx hashes + "no critical alerts" note under artifacts/ops/
```

---

## Шаг 5 — Collect + validate (strict contracts) + Evidence Report

After raw `artifacts/ops/*` exist:

```bash
pip install -r scripts/ops/requirements-ops.txt
# LIVE (required for GLOBAL GO eligibility):
./scripts/ops/collect_artifacts.sh
# Demo/schema-only (CI dry-run; NEVER GLOBAL GO):
# COLLECT_MODE=demo ./scripts/ops/collect_artifacts.sh
```

Produces `docs/ops/evidence/{kms_smoke,iam_audit,paging_drill,shadow_canary,verdict}.json`.  
Pydantic rejects `drift_detected: true`, `sla_met: false`, failed sign, etc.

Also update [`FINAL-GO-LIVE-EVIDENCE-REPORT.md`](FINAL-GO-LIVE-EVIDENCE-REPORT.md), then request human **GLOBAL GO / NO-GO**.

**Do not** treat `COLLECT_MODE=demo` or schema-only PASS as GLOBAL GO.
