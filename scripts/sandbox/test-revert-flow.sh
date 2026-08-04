#!/usr/bin/env bash
# test-revert-flow.sh — Anvil e2e: reverting rescue tx → ReceiptWatcher → dedup release → retry
#
# Scenario:
#   1. Deploy RevertOnWithdraw honeypot on local Anvil
#   2. PrepareRescue locks dedup
#   3. Send withdraw() that reverts (balance changed after snapshot)
#   4. ReceiptWatcher releases dedup on status=0
#   5. Second PrepareRescue succeeds (clear_to_sign)
set -euo pipefail

SANDBOX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SANDBOX/../.." && pwd)"
CONTRACTS="$SANDBOX/contracts"
RPC="${RPC_URL:-http://127.0.0.1:8545}"
REPORT="$ROOT/artifacts/stress_test/revert-flow-e2e.json"

require_tools() {
  command -v anvil >/dev/null || { echo "[FAIL] anvil not found"; exit 1; }
  command -v cast >/dev/null || { echo "[FAIL] cast not found"; exit 1; }
  command -v forge >/dev/null || { echo "[FAIL] forge not found"; exit 1; }
  command -v go >/dev/null || { echo "[FAIL] go not found"; exit 1; }
}

echo "=== REVERT FLOW E2E (Anvil) ==="
require_tools

# Local Anvil only — never mainnet
"$SANDBOX/start-anvil.sh"
"$SANDBOX/setup-anvil-env.sh" 2>/dev/null || true
ENV_FILE="${SANDBOX_ENV:-$("$SANDBOX/resolve-anvil-env.sh")}"
# shellcheck disable=SC1090
set -a && source "$ENV_FILE" && set +a

MNEMONIC="${ANVIL_MNEMONIC:-test test test test test test test test test test test junk}"
BOT_INDEX="${ANVIL_BOT_INDEX:-1}"
# Local Anvil signing key (fork env may omit BOT_PRIVATE_KEY)
if [[ -z "${BOT_PRIVATE_KEY:-}" ]]; then
  BOT_PRIVATE_KEY="$(cast wallet private-key --mnemonic "$MNEMONIC" --mnemonic-index "$BOT_INDEX")"
  BOT_ADDRESS="$(cast wallet address --mnemonic "$MNEMONIC" --mnemonic-index "$BOT_INDEX")"
fi
# Field funder allowlist (attack #06) — use recon authority, not mnemonic wallet
FUNDER="${ALLOWED_FUNDER:-0x730ea0231808f42a20f8921ba7fbc788226768f5}"
BOT="${BOT_ADDRESS:?BOT_ADDRESS missing}"
BOT_KEY="${BOT_PRIVATE_KEY:?BOT_PRIVATE_KEY missing}"

echo "[build] RevertOnWithdraw.sol"
forge build --root "$CONTRACTS" --force >/dev/null

echo "[deploy] honeypot contract"
DEPLOY_LOG=$(forge create RevertOnWithdraw.sol:RevertOnWithdraw \
  --root "$CONTRACTS" \
  --rpc-url "$RPC" \
  --private-key "$BOT_KEY" \
  --broadcast 2>&1)
CONTRACT=$(echo "$DEPLOY_LOG" | awk '/Deployed to:/ {print $3}')
if [[ -z "$CONTRACT" ]]; then
  echo "$DEPLOY_LOG"
  echo "[FAIL] contract deploy"
  exit 1
fi
echo "       contract=$CONTRACT"

echo "[fund] seed contract balance"
cast send "$CONTRACT" --value 1ether --rpc-url "$RPC" --private-key "$BOT_KEY" >/dev/null

echo "[snap] honeypot balance snapshot (must be mined before bump)"
cast send "$CONTRACT" "snapshot()" --rpc-url "$RPC" --private-key "$BOT_KEY" >/dev/null

echo "[bump] change contract balance (triggers BLOCK on withdraw)"
cast send "$CONTRACT" --value 0.1ether --rpc-url "$RPC" --private-key "$BOT_KEY" >/dev/null

echo "[revert] withdraw must revert with BLOCK"
DATA=$(cast calldata "withdraw(address,uint256)" "$FUNDER" 1)
TX_JSON=$(cast send "$CONTRACT" --data "$DATA" --gas-limit 300000 \
  --rpc-url "$RPC" --private-key "$BOT_KEY" --json)
TX_HASH=$(echo "$TX_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('transactionHash','')); assert d.get('status') in ('0x0', 0, '0'), d")
if [[ -z "$TX_HASH" ]]; then
  echo "$TX_JSON"
  echo "[FAIL] reverting tx missing hash"
  exit 1
fi
echo "       revert_tx=$TX_HASH"

export RUN_REVERT_E2E=1
export RPC_URL="$RPC"
export REVERT_CONTRACT="$CONTRACT"
export REVERT_TX_HASH="$TX_HASH"
export BOT_ADDRESS="$BOT"
export BOT_PRIVATE_KEY="$BOT_KEY"
export FUNDER_ADDRESS="$FUNDER"
export ALLOWED_FUNDERS="$FUNDER"

echo "[test] Go e2e orchestrator + ReceiptWatcher"
cd "$ROOT/cmd/agent"
if ! go test ./internal/orchestrator/ -run TestRevertFlowAnvilE2E -count=1 -v -timeout 3m; then
  echo "[FAIL] revert flow e2e"
  exit 1
fi

python3 - "$REPORT" "$CONTRACT" <<'PY'
import json, sys, time
from pathlib import Path
report = {
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "status": "PASS",
    "revert_contract": sys.argv[2],
    "dedup_released_on_revert": True,
    "retry_prepare_rescue": "clear_to_sign",
    "chain": "anvil_local",
}
Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n")
print(f"[OK] {sys.argv[1]}")
PY

echo "[OK] revert flow e2e PASS"
