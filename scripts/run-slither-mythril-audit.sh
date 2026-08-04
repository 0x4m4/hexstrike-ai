#!/usr/bin/env bash
# Slither + Mythril для implementation и ProxyAdmin (Rhino.fi BSC)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export BSC_RPC="${BSC_RPC:-http://51.222.42.220:8545}"
OUT="${ROOT}/artifacts/slither-mythril"

echo "[+] BSC_RPC=$BSC_RPC"
echo "[+] BSCSCAN_API_KEY=${BSCSCAN_API_KEY:-NOT SET — Slither on-chain может упасть}"
echo "[+] Out: $OUT"

python3 "${ROOT}/scripts/run-slither-mythril-audit.py" \
  --out "$OUT" \
  --rpc "$BSC_RPC"
