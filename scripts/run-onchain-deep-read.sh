#!/usr/bin/env bash
# Локальный запуск on-chain deep read (Mac/Linux). Только stdlib Python 3.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/scripts/onchain-proxy-deep-read.py"
PROXY="${1:-0xb80a582fa430645a043bb4f6135321ee01005fef}"
OUT="${2:-${ROOT}/artifacts/onchain-deep-read}"
RPC="${BSC_RPC:-http://51.222.42.220:8545}"

if [[ ! -f "$SCRIPT" ]]; then
  echo "[!] Нет $SCRIPT"
  echo "    git pull origin cursor/dual-mode-agent-b0a0"
  echo "    или: curl -fsSL -o $SCRIPT \\"
  echo "      https://raw.githubusercontent.com/Banda198565/hexstrike-ai/cursor/dual-mode-agent-b0a0/scripts/onchain-proxy-deep-read.py"
  exit 1
fi

echo "[+] RPC: $RPC"
echo "[+] Proxy: $PROXY"
echo "[+] Out: $OUT"
python3 "$SCRIPT" "$PROXY" --rpc "$RPC" --out "$OUT"
