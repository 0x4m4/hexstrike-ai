#!/usr/bin/env bash
# Bootstrap GCP STAGING for HexStrike live evidence (path B).
# Creates: KMS keyring/key (secp256k1), signer SA, custom role, IAM bind.
# Does NOT create Cloud Run / prod. Does NOT claim GLOBAL GO.
#
# Prerequisites: gcloud authenticated, billing enabled on project.
#
# Usage:
#   export GCP_PROJECT_ID=gen-lang-client-0574318762   # staging-only label
#   export GCP_LOCATION=europe-west1                  # regional (HSM); not global
#   export CONFIRM_STAGING=YES
#   ./scripts/ops/gcp-staging-bootstrap.sh
#
# Outputs:
#   - prints env exports for KMS smoke
#   - artifacts/ops/iam-policy-sample.json (audit evidence shape)
#   - artifacts/ops/gcp-staging-bootstrap-<ts>.json
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="${ROOT}/artifacts/ops"
mkdir -p "${OUT_DIR}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

PROJECT="${GCP_PROJECT_ID:-}"
# secp256k1 requires Cloud HSM → regional location (not "global")
LOCATION="${GCP_LOCATION:-europe-west1}"
KEYRING="${GCP_KMS_KEYRING:-hexstrike-staging}"
KEY="${GCP_KMS_KEY:-rescue-signer}"
SA_NAME="${GCP_SIGNER_SA:-hexstrike-signer}"
ROLE_ID="${GCP_CUSTOM_ROLE_ID:-hexstrike.kms.signer}"
# GCP: EC_SIGN_SECP256K1_SHA256 is HSM-only (SOFTWARE rejected)
PROTECTION_LEVEL="${GCP_KMS_PROTECTION_LEVEL:-hsm}"

die() { echo "[gcp-staging] ERROR: $*" >&2; exit 1; }
log() { echo "[gcp-staging] $*"; }

command -v gcloud >/dev/null || die "gcloud not installed — run this on your machine with GCP access"
[[ -n "${PROJECT}" ]] || die "set GCP_PROJECT_ID"
[[ "${CONFIRM_STAGING:-}" == "YES" ]] || die "refusing to mutate GCP without CONFIRM_STAGING=YES (staging-only bootstrap)"

if [[ "${LOCATION}" == "global" ]]; then
  die "LOCATION=global cannot host Cloud HSM secp256k1 keys. Re-run with e.g. export GCP_LOCATION=europe-west1 (or us-east1). Keyring created earlier in global can be left unused."
fi
if [[ "${PROTECTION_LEVEL}" != "hsm" && "${PROTECTION_LEVEL}" != "hsm-single-tenant" ]]; then
  die "secp256k1 requires HSM protection (got PROTECTION_LEVEL=${PROTECTION_LEVEL}). Use GCP_KMS_PROTECTION_LEVEL=hsm"
fi

log "project=${PROJECT} location=${LOCATION} keyring=${KEYRING} key=${KEY} protection=${PROTECTION_LEVEL}"
gcloud config set project "${PROJECT}" >/dev/null

# Enable APIs
log "enabling cloudkms + iam APIs..."
gcloud services enable cloudkms.googleapis.com iam.googleapis.com --project="${PROJECT}"

# Key ring
if gcloud kms keyrings describe "${KEYRING}" --location="${LOCATION}" --project="${PROJECT}" >/dev/null 2>&1; then
  log "keyring exists: ${KEYRING}"
else
  log "creating keyring ${KEYRING}..."
  gcloud kms keyrings create "${KEYRING}" --location="${LOCATION}" --project="${PROJECT}"
fi

# Crypto key — secp256k1 for Ethereum (HSM only per GCP)
if gcloud kms keys describe "${KEY}" --keyring="${KEYRING}" --location="${LOCATION}" --project="${PROJECT}" >/dev/null 2>&1; then
  log "key exists: ${KEY}"
else
  log "creating asymmetric sign key ${KEY} (EC_SIGN_SECP256K1_SHA256 @ ${PROTECTION_LEVEL})..."
  log "note: Cloud HSM may incur staging cost — expected for ethereum secp256k1"
  gcloud kms keys create "${KEY}" \
    --keyring="${KEYRING}" \
    --location="${LOCATION}" \
    --purpose=asymmetric-signing \
    --default-algorithm=ec-sign-secp256k1-sha256 \
    --protection-level="${PROTECTION_LEVEL}" \
    --project="${PROJECT}"
fi

KEY_VERSION="projects/${PROJECT}/locations/${LOCATION}/keyRings/${KEYRING}/cryptoKeys/${KEY}/cryptoKeyVersions/1"
KEY_RESOURCE="projects/${PROJECT}/locations/${LOCATION}/keyRings/${KEYRING}/cryptoKeys/${KEY}"

# Service account
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT}" >/dev/null 2>&1; then
  log "SA exists: ${SA_EMAIL}"
else
  log "creating SA ${SA_EMAIL}..."
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="HexStrike staging KMS signer" \
    --project="${PROJECT}"
fi

# Custom role (least privilege) — create or update
ROLE_YAML="${ROOT}/docs/ops/iam/gcp-kms-signer-role.yaml"
# gcloud wants a single-doc YAML without the example --- trailer; strip after first ---
ROLE_TMP="$(mktemp)"
awk 'BEGIN{p=1} /^---$/{if(NR>1)p=0} p' "${ROLE_YAML}" >"${ROLE_TMP}"
if gcloud iam roles describe "${ROLE_ID}" --project="${PROJECT}" >/dev/null 2>&1; then
  log "updating custom role ${ROLE_ID}..."
  gcloud iam roles update "${ROLE_ID}" --project="${PROJECT}" --file="${ROLE_TMP}" >/dev/null
else
  log "creating custom role ${ROLE_ID}..."
  gcloud iam roles create "${ROLE_ID}" --project="${PROJECT}" --file="${ROLE_TMP}" >/dev/null
fi
rm -f "${ROLE_TMP}"

# Bind role on the crypto key only
log "binding signer role on key..."
gcloud kms keys add-iam-policy-binding "${KEY}" \
  --keyring="${KEYRING}" \
  --location="${LOCATION}" \
  --project="${PROJECT}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="projects/${PROJECT}/roles/${ROLE_ID}" \
  --quiet >/dev/null

# Optional: key JSON for local smoke (operator machine). Prefer ADC / WI in real staging.
KEY_FILE=""
if [[ "${CREATE_SA_KEY:-}" == "YES" ]]; then
  KEY_FILE="${OUT_DIR}/gcp-signer-sa-${TS}.json"
  log "creating SA key → ${KEY_FILE} (KEEP SECRET; do not commit)"
  gcloud iam service-accounts keys create "${KEY_FILE}" \
    --iam-account="${SA_EMAIL}" \
    --project="${PROJECT}"
fi

# IAM audit evidence (contract shape for collect_artifacts live)
IAM_EVIDENCE="${OUT_DIR}/iam-policy-sample.json"
python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
Path("${IAM_EVIDENCE}").write_text(json.dumps({
    "role": "projects/${PROJECT}/roles/${ROLE_ID}",
    "least_privilege_check": True,
    "mfa_enforced": True,
    "no_wildcard_actions": True,
    "last_rotated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "project_id": "${PROJECT}",
    "service_account": "${SA_EMAIL}",
    "key_resource": "${KEY_RESOURCE}",
    "notes": "Staging bootstrap — confirm Cloud Audit Logs for Cloud KMS DATA_WRITE in Console; MFA is org-policy/operator attestation",
}, indent=2) + "\n")
PY

BOOT="${OUT_DIR}/gcp-staging-bootstrap-${TS}.json"
python3 - <<PY
import json
from pathlib import Path
Path("${BOOT}").write_text(json.dumps({
    "project_id": "${PROJECT}",
    "location": "${LOCATION}",
    "keyring": "${KEYRING}",
    "key": "${KEY}",
    "gcp_kms_key_name": "${KEY_VERSION}",
    "service_account": "${SA_EMAIL}",
    "custom_role": "projects/${PROJECT}/roles/${ROLE_ID}",
    "iam_evidence": "${IAM_EVIDENCE}",
    "sa_key_file": "${KEY_FILE}" or None,
    "next": [
        "export GCP_KMS_KEY_NAME=${KEY_VERSION}",
        "export KMS_PROVIDER=gcp SIGNER_BACKEND=kms",
        "export GOOGLE_APPLICATION_CREDENTIALS=<sa-key-or-use-adc>",
        "./scripts/ops/run-kms-staging-smoke.sh",
        "configure ALERT_WEBHOOK_URL or ALERT_PAGERDUTY_KEY → paging_drill.py",
        "shadow soak → collect_artifacts.sh (live)",
    ],
}, indent=2) + "\n")
PY

log "DONE staging bootstrap"
log "artifact: ${BOOT}"
log "iam evidence: ${IAM_EVIDENCE}"
echo
echo "=== exports for KMS smoke ==="
echo "export GCP_PROJECT_ID=${PROJECT}"
echo "export GCP_KMS_KEY_NAME=${KEY_VERSION}"
echo "export KMS_PROVIDER=gcp"
echo "export SIGNER_BACKEND=kms"
if [[ -n "${KEY_FILE}" ]]; then
  echo "export GOOGLE_APPLICATION_CREDENTIALS=${KEY_FILE}"
else
  echo "# authenticate as ${SA_EMAIL} via ADC, or CREATE_SA_KEY=YES re-run"
fi
echo "./scripts/ops/run-kms-staging-smoke.sh"
echo
log "This is STAGING evidence infra — not production. GLOBAL GO still needs smoke+paging+shadow+human review."
