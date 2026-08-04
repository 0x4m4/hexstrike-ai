#!/usr/bin/env bash
# run-step3-defensive.sh — Step 3 (defensive): hardened bot via logging proxy
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SANDBOX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SANDBOX_ENV:-$("$SANDBOX/resolve-anvil-env.sh")}"
PROXY_PORT="${PROXY_PORT:-8546}"
UPSTREAM_RPC="${UPSTREAM_RPC:-http://127.0.0.1:8545}"
PROXY_URL="http://127.0.0.1:${PROXY_PORT}"
INTERCEPTOR_PID="${TMPDIR:-/tmp}/hexstrike-interceptor.pid"
INTERCEPTOR_LOG="${TMPDIR:-/tmp}/hexstrike-interceptor.log"

cd "$ROOT"

echo "=== HexStrike Sandbox — Step 3 DEFENSIVE (hardening) ==="
echo ""

VENV="$SANDBOX/.venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r "$SANDBOX/requirements-sandbox.txt"
fi
PYTHON="$VENV/bin/python"

"$SANDBOX/start-anvil.sh"

if [[ ! -f "$INTERCEPTOR_PID" ]] || ! kill -0 "$(cat "$INTERCEPTOR_PID")" 2>/dev/null; then
  echo "[start] RPC interceptor $PROXY_URL → $UPSTREAM_RPC"
  UPSTREAM_RPC="$UPSTREAM_RPC" PROXY_PORT="$PROXY_PORT" \
    nohup "$PYTHON" "$SANDBOX/rpc_interceptor.py" >"$INTERCEPTOR_LOG" 2>&1 &
  echo $! >"$INTERCEPTOR_PID"
  sleep 2
fi

curl -sf --max-time 3 "${PROXY_URL}/health" >/dev/null || {
  echo "[FAIL] Interceptor down"; tail -20 "$INTERCEPTOR_LOG"; exit 1
}

echo ""
echo "Hardening enabled:"
echo "  • multi-source balance (proxy vs direct Anvil)"
echo "  • anomaly: balance drop without on-chain tx"
echo "  • pre-sign verify on direct RPC"
echo ""
echo "Alerts → artifacts/sandbox/anomaly-alerts.jsonl"
echo ""
echo "Simulate low balance (direct Anvil — both sources agree):"
echo "  source $ENV_FILE && ./scripts/sandbox/set-balance.sh \$BOT_ADDRESS 300000000000000000"
echo ""
echo "Starting hardened bot (Ctrl+C to stop)..."
echo ""

export SANDBOX_ENV="$ENV_FILE"
export RPC_URL="$PROXY_URL"
export DIRECT_RPC_URL="$UPSTREAM_RPC"
export UPSTREAM_RPC="$UPSTREAM_RPC"
export HARDENING_ENABLED=true
exec python3 "$SANDBOX/dummy_bot.py"
