#!/usr/bin/env bash
# Staging smoke: real AWS or GCP KMS sign + fail-closed negatives.
# LOCAL / STAGING ONLY — never commit credentials.
#
# Usage:
#   export KMS_PROVIDER=aws AWS_KMS_KEY_ID=... AWS_REGION=... SIGNER_ADDRESS=0x...
#   ./scripts/ops/run-kms-staging-smoke.sh
#   # or: KMS_PROVIDER=gcp GCP_KMS_KEY_NAME=projects/.../cryptoKeyVersions/1
#
# Artifacts → artifacts/ops/kms-smoke-<ts>/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${ROOT}/artifacts/ops/kms-smoke-${TS}"
mkdir -p "${OUT}"

PROVIDER="${KMS_PROVIDER:-aws}"
export GO_LIVE_PHASE="${GO_LIVE_PHASE:-canary}"
export SIGNER_BACKEND=kms
export KMS_PROVIDER="${PROVIDER}"

log() { echo "[kms-smoke] $*" | tee -a "${OUT}/smoke.log"; }

require() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    log "FAIL fail-closed: missing ${name}"
    echo "{\"case\":\"missing_${name}\",\"result\":\"FAIL_CLOSED\",\"ok\":true}" >>"${OUT}/cases.jsonl"
    return 1
  fi
  return 0
}

log "provider=${PROVIDER} phase=${GO_LIVE_PHASE} out=${OUT}"

# --- Fail-closed: no key id ---
(
  unset AWS_KMS_KEY_ID GCP_KMS_KEY_NAME || true
  cd "${ROOT}/cmd/agent"
  if go test ./internal/signer/ -run TestNewFromEnv_KMSFailClosedWithoutCloudConfig -count=1 >>"${OUT}/unit-failclosed.log" 2>&1; then
    echo '{"case":"unit_failclosed_no_cloud_config","result":"PASS","ok":true}' >>"${OUT}/cases.jsonl"
    log "PASS unit fail-closed without cloud config"
  else
    echo '{"case":"unit_failclosed_no_cloud_config","result":"FAIL","ok":false}' >>"${OUT}/cases.jsonl"
    log "FAIL unit fail-closed"
    exit 1
  fi
)

# --- Fail-closed: local_key outside lab ---
(
  cd "${ROOT}/cmd/agent"
  if go test ./internal/signer/ -run TestLocalKeyForbiddenOutsideLab -count=1 >>"${OUT}/unit-localkey.log" 2>&1; then
    echo '{"case":"local_key_forbidden_outside_lab","result":"PASS","ok":true}' >>"${OUT}/cases.jsonl"
    log "PASS local_key forbidden outside lab"
  else
    echo '{"case":"local_key_forbidden_outside_lab","result":"FAIL","ok":false}' >>"${OUT}/cases.jsonl"
    exit 1
  fi
)

# --- Live KMS (requires credentials) ---
LIVE=0
if [[ "${PROVIDER}" == "aws" || "${PROVIDER}" == "" ]]; then
  if [[ -n "${AWS_KMS_KEY_ID:-}" && -n "${AWS_REGION:-}" ]]; then
    LIVE=1
  else
    log "SKIP live AWS: set AWS_KMS_KEY_ID + AWS_REGION (and credentials)"
    echo '{"case":"live_aws_sign","result":"SKIP_NO_CREDS","ok":null,"operator_owned":true}' >>"${OUT}/cases.jsonl"
  fi
elif [[ "${PROVIDER}" == "gcp" || "${PROVIDER}" == "google" ]]; then
  if [[ -n "${GCP_KMS_KEY_NAME:-}" ]]; then
    LIVE=1
  else
    log "SKIP live GCP: set GCP_KMS_KEY_NAME (+ ADC)"
    echo '{"case":"live_gcp_sign","result":"SKIP_NO_CREDS","ok":null,"operator_owned":true}' >>"${OUT}/cases.jsonl"
  fi
fi

if [[ "${LIVE}" == "1" ]]; then
  cd "${ROOT}/cmd/agent"
  if go test ./internal/signer/ -tags=live_kms -run TestLiveKMS_SignTx -count=1 -v >"${OUT}/live-sign.log" 2>&1; then
    echo "{\"case\":\"live_${PROVIDER}_sign\",\"result\":\"PASS\",\"ok\":true,\"log\":\"live-sign.log\"}" >>"${OUT}/cases.jsonl"
    log "PASS live ${PROVIDER} SignTx"
  else
    echo "{\"case\":\"live_${PROVIDER}_sign\",\"result\":\"FAIL\",\"ok\":false,\"log\":\"live-sign.log\"}" >>"${OUT}/cases.jsonl"
    log "FAIL live ${PROVIDER} SignTx — see ${OUT}/live-sign.log"
    exit 1
  fi
fi

# Summary (schema aligned with GLOBAL-GO-OPERATOR-RUNBOOK §4c)
python3 - <<PY
import json, pathlib
out = pathlib.Path("${OUT}")
provider = "${PROVIDER}" or "aws"
cases = []
p = out / "cases.jsonl"
if p.exists():
    for line in p.read_text().splitlines():
        if line.strip():
            cases.append(json.loads(line))
failed = [c for c in cases if c.get("ok") is False]
skipped = [c for c in cases if str(c.get("result", "")).startswith("SKIP")]
passed = [c for c in cases if c.get("ok") is True]
fc_cases = [
    c for c in cases
    if c.get("case") in ("unit_failclosed_no_cloud_config", "local_key_forbidden_outside_lab")
]
fc_ok = bool(fc_cases) and all(c.get("ok") is True for c in fc_cases)
live = next((c for c in cases if "live_" in c.get("case", "") and "sign" in c.get("case", "")), None)
if live is None:
    sign_test = "missing"
elif live.get("result", "").startswith("SKIP"):
    sign_test = "skip"
elif live.get("ok") is True:
    sign_test = "ok"
else:
    sign_test = "fail"
if failed:
    result = "FAIL"
elif sign_test == "skip":
    result = "PASS_WITH_OPERATOR_SKIP"
elif sign_test == "ok" and fc_ok:
    result = "PASS"
else:
    result = "FAIL"
summary = {
    "result": result,
    "provider": provider,
    "sign_test": sign_test,
    "fail_closed_test": "ok" if fc_ok else "fail",
    "artifact_dir": str(out),
    "passed": len(passed),
    "failed": len(failed),
    "skipped_operator": len(skipped),
    "cases": cases,
    "verdict": result,
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
if failed or result == "FAIL":
    raise SystemExit(1)
PY

log "done → ${OUT}/summary.json"
