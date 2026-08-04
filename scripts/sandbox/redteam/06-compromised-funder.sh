#!/usr/bin/env bash
# 06-compromised-funder.sh — FUNDER points to attacker; bot sends rescue there
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"
require_tools

echo "=== REDTEAM 06: compromised FUNDER_ADDRESS ==="
reset_bot_balance
before="$(snapshot_events)"

# Temp env: rescue goes to attacker instead of real funder
start_bot_background "HARDENING_ENABLED=false FUNDER_ADDRESS=$ATTACKER"
"$SANDBOX/set-balance.sh" "$BOT" "$LOW_BAL" >/dev/null
sleep 5
signed="$(count_signed_since "$before")"
attacker_before="$(cast balance "$ATTACKER" --rpc-url "$RPC")"
stop_bot
sleep 1
attacker_after="$(cast balance "$ATTACKER" --rpc-url "$RPC")"
reset_bot_balance

if [[ "$signed" -ge 1 ]] && [[ "$attacker_after" -gt "$attacker_before" ]]; then
  log_result "06-compromised-funder" "VULN_CONFIRMED" "rescue value sent to attacker $ATTACKER — no allowlist"
elif [[ "$signed" -ge 1 ]]; then
  log_result "06-compromised-funder" "VULN_CONFIRMED" "bot signed $signed tx(s) with compromised FUNDER_ADDRESS=$ATTACKER"
else
  log_result "06-compromised-funder" "INCONCLUSIVE" "signed=$signed attacker_delta=$((attacker_after - attacker_before))"
fi
