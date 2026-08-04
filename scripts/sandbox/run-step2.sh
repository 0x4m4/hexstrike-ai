#!/usr/bin/env bash
# run-step2.sh — Step 2: Anvil + transparent RPC interceptor + bot via proxy
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

echo "=== HexStrike Sandbox — Step 2 (RPC Interceptor) ==="
echo ""

# deps (local venv — avoids system pip conflicts)
VENV="$SANDBOX/.venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "[install] creating sandbox venv..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r "$SANDBOX/requirements-sandbox.txt"
elif ! "$VENV/bin/python" -c "import fastapi, httpx, uvicorn" 2>/dev/null; then
  "$VENV/bin/pip" install -q -r "$SANDBOX/requirements-sandbox.txt"
fi
PYTHON="$VENV/bin/python"

"$SANDBOX/start-anvil.sh"

if [[ -f "$INTERCEPTOR_PID" ]] && kill -0 "$(cat "$INTERCEPTOR_PID")" 2>/dev/null; then
  echo "[OK]   Interceptor already running (pid $(cat "$INTERCEPTOR_PID"))"
else
  echo "[start] RPC interceptor $PROXY_URL → $UPSTREAM_RPC"
  UPSTREAM_RPC="$UPSTREAM_RPC" PROXY_PORT="$PROXY_PORT" \
    nohup "$PYTHON" "$SANDBOX/rpc_interceptor.py" >"$INTERCEPTOR_LOG" 2>&1 &
  echo $! >"$INTERCEPTOR_PID"
  sleep 2
fi

if curl -sf --max-time 3 "${PROXY_URL}/health" >/dev/null; then
  echo "[OK]   Interceptor health OK"
else
  echo "[FAIL] Interceptor not responding. Log:"
  tail -30 "$INTERCEPTOR_LOG" || true
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[FAIL] Env file missing: $ENV_FILE"
  exit 1
fi

echo ""
echo "Bot will use RPC via proxy:"
echo "  BOT → $PROXY_URL → $UPSTREAM_RPC"
echo ""
echo "Logs:"
echo "  interceptor: artifacts/sandbox/rpc-interceptor.jsonl"
echo "  bot events : artifacts/sandbox/dummy-bot-events.jsonl"
echo ""
echo "Test drain (other terminal):"
echo "  source $ENV_FILE && ./scripts/sandbox/set-balance.sh \$BOT_ADDRESS 300000000000000000"
echo ""
echo "Starting dummy bot (Ctrl+C to stop)..."
echo ""

export SANDBOX_ENV="$ENV_FILE"
export RPC_URL="$PROXY_URL"
exec python3 "$SANDBOX/dummy_bot.py"
