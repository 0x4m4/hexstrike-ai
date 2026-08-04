#!/usr/bin/env bash
# HexStrike ALL forensics modules — read-only IOC + workflow bundle
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=/dev/null
source "$ROOT/scripts/forensics-env-mac.sh"

export HEXSTRIKE_MODE="${HEXSTRIKE_MODE:-forensics}"
RUNNER="$ROOT/scripts/run-forensics-module.sh"

# Seed recon inputs from tracked templates
mkdir -p "$ROOT/artifacts/recon" "$ROOT/artifacts/intel"
if [[ -d "$ROOT/docs/recon" ]]; then
  cp -n "$ROOT/docs/recon/"* "$ROOT/artifacts/recon/" 2>/dev/null || cp "$ROOT/docs/recon/"* "$ROOT/artifacts/recon/" 2>/dev/null || true
fi
if [[ -d "$ROOT/docs/recon/vanilla-drainer-intel" ]]; then
  mkdir -p "$ROOT/artifacts/recon/vanilla-drainer-intel"
  cp -a "$ROOT/docs/recon/vanilla-drainer-intel/." "$ROOT/artifacts/recon/vanilla-drainer-intel/" 2>/dev/null || true
fi
if [[ -d "$ROOT/docs/intel" ]]; then
  cp -a "$ROOT/docs/intel/." "$ROOT/artifacts/intel/" 2>/dev/null || true
fi

echo "=== HexStrike ALL forensics modules ==="
echo "mode: ${HEXSTRIKE_MODE}"
echo "────────────────────────────────────────"

failed=0
run_one() {
  local label="$1" agent="$2" task="$3" analyze="$4" workflow="$5"
  if ! bash "$RUNNER" "$label" "$agent" "$task" "$analyze" "$workflow"; then
    echo "[FAIL] ${workflow}"
    failed=$((failed + 1))
  fi
  echo "────────────────────────────────────────"
}

run_one "TRX Drainer"     "Agent-Malware-08" "static-ioc-extract"    "trx"        "trx-drainer-forensics"
run_one "EVM Drainer"     "Agent-Malware-09" "static-ioc-extract"    "evm"        "evm-drainer-forensics"
run_one "ApeTerminal"     "Agent-Malware-10" "static-ioc-extract"    "apeterminal" "apeterminal-forensics"
run_one "Solana Drainer"  "Agent-Malware-11" "static-ioc-extract"    "solana"     "solana-drainer-forensics"
run_one "Vanilla Drainer" "Agent-Malware-12" "osint-ioc-extract"     "vanilla"    "vanilla-drainer-forensics"
run_one "Permit Farming"  "Agent-Contract-03" "permit-farming-analyze" "permit"  "permit-farming-forensics"
run_one "CREATE2"         "Agent-Contract-04" "create2-analyze"       "create2"    "create2-forensics"

echo "=== ALL forensics complete (failed=${failed}) ==="
echo "${failed}" > "$ROOT/artifacts/forensics/.last-run-failed"
echo "Artifacts: ${ROOT}/artifacts/*-iocs.json"
exit $(( failed > 0 ? 1 : 0 ))
