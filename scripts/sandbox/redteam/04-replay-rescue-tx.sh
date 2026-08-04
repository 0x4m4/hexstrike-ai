#!/usr/bin/env bash
# 04-replay-rescue-tx.sh — replay last signed tx hash (should fail on Anvil)
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"
require_tools

echo "=== REDTEAM 04: replay rescue tx ==="
reset_bot_balance
before="$(snapshot_events)"
start_bot_background "HARDENING_ENABLED=false"
"$SANDBOX/set-balance.sh" "$BOT" "$LOW_BAL" >/dev/null
sleep 5
stop_bot

tx_hash="$(python3 - "$EVENTS" "$before" <<'PY'
import json, sys
path, since = sys.argv[1], int(sys.argv[2])
for line in reversed(open(path).read().splitlines()[since:]):
    d = json.loads(line)
    if d.get("result") == "signed" and d.get("tx_hash"):
        print(d["tx_hash"]); break
PY
)"

if [[ -z "${tx_hash:-}" ]]; then
  log_result "04-replay-rescue-tx" "SKIP" "no signed tx to replay"
  exit 0
fi

# Fetch raw tx and try send twice
raw="$(cast rpc eth_getRawTransactionByHash "$tx_hash" --rpc-url "$RPC" 2>/dev/null | tr -d '"')"
if [[ -z "$raw" || "$raw" == "null" ]]; then
  raw="$(cast tx "$tx_hash" --rpc-url "$RPC" --json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('raw',''))" 2>/dev/null || true)"
fi
if [[ -z "$raw" || "$raw" == "null" ]]; then
  # Anvil: re-broadcast same hash
  if cast rpc eth_sendRawTransaction "$(cast tx "$tx_hash" --rpc-url "$RPC" 2>/dev/null | head -1)" --rpc-url "$RPC" 2>&1 | grep -qi "already known\|nonce"; then
    log_result "04-replay-rescue-tx" "DEFENDED" "node rejected duplicate"
  else
    log_result "04-replay-rescue-tx" "INCONCLUSIVE" "could not extract raw tx"
  fi
  exit 0
fi

out1="$(cast rpc eth_sendRawTransaction "$raw" --rpc-url "$RPC" 2>&1 || true)"
out2="$(cast rpc eth_sendRawTransaction "$raw" --rpc-url "$RPC" 2>&1 || true)"
if echo "$out2" | grep -qiE "already known|nonce too low|replacement transaction underpriced"; then
  log_result "04-replay-rescue-tx" "DEFENDED" "second broadcast rejected: $out2"
else
  log_result "04-replay-rescue-tx" "VULN_CONFIRMED" "replay may have succeeded twice"
fi

reset_bot_balance
