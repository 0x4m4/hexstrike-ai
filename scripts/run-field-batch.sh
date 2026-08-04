#!/usr/bin/env bash
# Batch on-chain probe по targets JSON.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS="${1:-${ROOT}/scripts/sandbox/field-targets-merged.json}"

if [[ -f "${ROOT}/.venv-audit/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.venv-audit/bin/activate"
fi

export BSC_RPC="${BSC_RPC:-http://51.222.42.220:8545}"

echo "[+] Targets: $TARGETS"
echo "[+] RPC: $BSC_RPC"
echo "[+] BSCSCAN_API_KEY=${BSCSCAN_API_KEY:-NOT SET}"

python3 "${ROOT}/scripts/run-field-batch.py" \
  --targets "$TARGETS" \
  --with-agent \
  --parallel 3
