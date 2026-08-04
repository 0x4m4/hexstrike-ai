#!/usr/bin/env bash
# test-live-rescue-loop.sh — E2E happy path on Anvil:
#   PrepareRescue → EIP-1559 sign → PuissantRelay.Submit (public fallback) → ReceiptWatcher
set -euo pipefail

SANDBOX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SANDBOX/../.." && pwd)"
RPC="${RPC_URL:-http://127.0.0.1:8545}"
REPORT="$ROOT/artifacts/stress_test/live-rescue-loop-e2e.json"

require_tools() {
  command -v anvil >/dev/null || { echo "[FAIL] anvil not found"; exit 1; }
  command -v cast >/dev/null || { echo "[FAIL] cast not found"; exit 1; }
  command -v go >/dev/null || { echo "[FAIL] go not found"; exit 1; }
}

echo "=== LIVE RESCUE LOOP E2E (Anvil) ==="
require_tools

# Fresh local Anvil — fixed nonce baseline for rescuer wallet
"$SANDBOX/stop-anvil.sh" 2>/dev/null || true
"$SANDBOX/start-anvil.sh"
sleep 1

MNEMONIC="${ANVIL_MNEMONIC:-test test test test test test test test test test test junk}"
BOT_INDEX="${ANVIL_BOT_INDEX:-1}"
BOT="$(cast wallet address --mnemonic "$MNEMONIC" --mnemonic-index "$BOT_INDEX")"
BOT_KEY="$(cast wallet private-key --mnemonic "$MNEMONIC" --mnemonic-index "$BOT_INDEX")"
FUNDER="${ALLOWED_FUNDER:-0x730ea0231808f42a20f8921ba7fbc788226768f5}"

# Fixed nonce for reproducible signing
cast rpc anvil_setNonce "$BOT" 0x0 --rpc-url "$RPC" >/dev/null 2>&1 || true

# Trigger: bot balance below THRESHOLD (0.5 ETH) — rescue required
LOW_BAL="${BOT_BALANCE_WEI:-300000000000000000}"   # 0.3 ETH
RESCUE_WEI="${RESCUE_VALUE_WEI:-1000000000000000}" # 0.001 ETH
cast rpc anvil_setBalance "$BOT" "$(python3 -c "print(hex(int('$LOW_BAL')))")" --rpc-url "$RPC" >/dev/null
echo "[trigger] bot=$BOT balance=${LOW_BAL} wei (< threshold)"
echo "[funder] safe wallet=$FUNDER"

export RUN_LIVE_LOOP_E2E=1
export RPC_URL="$RPC"
export RELAY_PUBLIC_RPC="$RPC"
export BOT_ADDRESS="$BOT"
export BOT_PRIVATE_KEY="$BOT_KEY"
export FUNDER_ADDRESS="$FUNDER"
export ALLOWED_FUNDERS="$FUNDER"
export BOT_BALANCE_WEI="$LOW_BAL"
export RESCUE_VALUE_WEI="$RESCUE_WEI"

echo "[test] PrepareRescue → sign → PuissantRelay.Submit → Watcher.Watch"
cd "$ROOT/cmd/agent"
if ! go test ./internal/orchestrator/ -run TestLiveRescueLoopAnvilE2E -count=1 -v -timeout 3m; then
  echo "[FAIL] live rescue loop e2e"
  exit 1
fi

python3 - "$REPORT" "$BOT" "$FUNDER" "$RESCUE_WEI" <<'PY'
import json, sys, time
from pathlib import Path
report = {
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "status": "SUCCESS",
    "bot": sys.argv[2],
    "funder": sys.argv[3],
    "rescue_value_wei": sys.argv[4],
    "relay_strategy": "public_mempool_fallback",
    "dedup_held_after_success": True,
    "chain": "anvil_local",
}
Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n")
print(f"[OK] {sys.argv[1]}")
PY

echo "[OK] live rescue loop e2e SUCCESS"
