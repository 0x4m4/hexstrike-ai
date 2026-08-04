#!/usr/bin/env bash
# start-anvil.sh — local hardfork sandbox (Foundry Anvil)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${ANVIL_PORT:-8545}"
HOST="${ANVIL_HOST:-127.0.0.1}"
PID_FILE="${TMPDIR:-/tmp}/hexstrike-anvil.pid"
LOG_FILE="${TMPDIR:-/tmp}/hexstrike-anvil.log"

if ! command -v anvil >/dev/null 2>&1; then
  echo "[FAIL] anvil not found."
  echo "       Install Foundry: curl -L https://foundry.paradigm.xyz | bash && foundryup"
  exit 1
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "[OK]   Anvil already running (pid $(cat "$PID_FILE"))"
  echo "       RPC: http://${HOST}:${PORT}"
  exit 0
fi

echo "[start] Anvil on http://${HOST}:${PORT} (chain-id 31337)"
nohup anvil \
  --host "$HOST" \
  --port "$PORT" \
  --chain-id 31337 \
  --accounts 10 \
  --balance 10000 \
  >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
sleep 2

if curl -sf --max-time 3 "http://${HOST}:${PORT}" \
  -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' >/dev/null; then
  echo "[OK]   Anvil ready — log: $LOG_FILE"
  echo "       Test accounts: https://book.getfoundry.sh/reference/anvil/"
  echo "       Stop: kill \$(cat $PID_FILE)"
else
  echo "[FAIL] Anvil did not respond. Tail log:"
  tail -20 "$LOG_FILE" || true
  exit 1
fi
