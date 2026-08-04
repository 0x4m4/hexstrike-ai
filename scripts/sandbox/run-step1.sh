#!/usr/bin/env bash
# run-step1.sh — Step 1 sandbox: Anvil + dummy bot (one command)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SANDBOX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SANDBOX_ENV:-$("$SANDBOX/resolve-anvil-env.sh")}"

cd "$ROOT"

echo "=== HexStrike Sandbox — Step 1 ==="
echo ""

"$SANDBOX/start-anvil.sh"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[FAIL] Env file missing: $ENV_FILE"
  exit 1
fi

# shellcheck disable=SC1090
set -a && source "$ENV_FILE" && set +a

echo ""
echo "[info] Bot wallet : ${BOT_ADDRESS:-unset}"
echo "[info] Threshold  : ${THRESHOLD_WEI:-unset} wei"
echo "[info] RPC        : ${RPC_URL:-http://127.0.0.1:8545}"
echo ""
echo "In another terminal, simulate drain:"
echo "  ./scripts/sandbox/set-balance.sh ${BOT_ADDRESS} 300000000000000000"
echo ""
echo "Starting dummy bot (Ctrl+C to stop)..."
echo ""

export SANDBOX_ENV="$ENV_FILE"
exec python3 "$SANDBOX/dummy_bot.py"
