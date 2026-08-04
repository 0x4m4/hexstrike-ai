# Staging smoke — real KMS (operator-owned)

## Goal

Prove `SIGNER_BACKEND=kms` signs with a **real** AWS or GCP key, and fail-closed paths still hold.

## Prerequisites

- Staging key: AWS `ECC_SECG_P256K1` or GCP `EC_SIGN_SECP256K1_SHA256`
- Runtime credentials (AWS default chain / GCP ADC) with least-privilege from `docs/ops/KMS-IAM-HARDENING.md`
- Optional `SIGNER_ADDRESS=0x...` bind check

## Run

```bash
# AWS
export KMS_PROVIDER=aws
export AWS_REGION=...
export AWS_KMS_KEY_ID=arn:aws:kms:...
export SIGNER_ADDRESS=0x...          # optional bind
export CHAIN_ID=56                   # digest chain (sign only; no broadcast)
./scripts/ops/run-kms-staging-smoke.sh

# GCP
export KMS_PROVIDER=gcp
export GCP_KMS_KEY_NAME=projects/.../cryptoKeyVersions/1
./scripts/ops/run-kms-staging-smoke.sh
```

## Expected artifacts

| File | Content |
| --- | --- |
| `artifacts/ops/kms-smoke-<ts>/smoke.log` | Human log |
| `artifacts/ops/kms-smoke-<ts>/cases.jsonl` | Pass/fail/skip per case |
| `artifacts/ops/kms-smoke-<ts>/live-sign.log` | Live `SignTx` verbose output |
| `artifacts/ops/kms-smoke-<ts>/summary.json` | Verdict |

## Cases

1. Unit fail-closed without cloud config — **must PASS** (no creds needed)
2. `local_key` forbidden outside lab — **must PASS**
3. Live SignTx — **operator** (SKIP without creds; PASS with real key)

## Evidence for GO_LIVE §4

Attach `summary.json` + redacted `live-sign.log` (address + tx hash only; no secrets).
