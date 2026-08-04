#!/usr/bin/env bash
# 03-front-run-drain.sh — attacker drains bot wallet via anvil_setBalance before rescue
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"
require_tools

echo "=== REDTEAM 03: front-run drain (balance race) ==="
reset_bot_balance
before="$(snapshot_events)"

# Start bot with fast poll
start_bot_background "HARDENING_ENABLED=false POLL_INTERVAL_SEC=1"

# Drop below threshold, brief window for bot poll, then zero balance
"$SANDBOX/set-balance.sh" "$BOT" "$LOW_BAL" >/dev/null
sleep 2
cast rpc anvil_setBalance "$BOT" "0x0" --rpc-url "$RPC" >/dev/null
sleep 4

signed="$(count_signed_since "$before")"
bal="$(cast balance "$BOT" --rpc-url "$RPC")"
stop_bot
reset_bot_balance

if [[ "$signed" -ge 1 ]] && [[ "$bal" == "0" ]]; then
  log_result "03-front-run-drain" "VULN_CONFIRMED" "bot signed but balance already 0 — gas/TOCTOU risk"
elif [[ "$signed" -eq 0 ]]; then
  log_result "03-front-run-drain" "DEFENDED" "bot did not sign (blocked_no_gas or no trigger)"
else
  log_result "03-front-run-drain" "INCONCLUSIVE" "signed=$signed balance=$bal"
fi
