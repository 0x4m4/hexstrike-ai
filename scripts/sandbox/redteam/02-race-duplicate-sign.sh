#!/usr/bin/env bash
# 02-race-duplicate-sign.sh — oscillate balance; check for duplicate rescue txs
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"
require_tools

echo "=== REDTEAM 02: race / duplicate sign ==="
reset_bot_balance
before="$(snapshot_events)"
start_bot_background "HARDENING_ENABLED=false"

for _ in {1..5}; do
  "$SANDBOX/set-balance.sh" "$BOT" "$LOW_BAL" >/dev/null
  sleep 3
  "$SANDBOX/set-balance.sh" "$BOT" "$HIGH_BAL" >/dev/null
  sleep 3
done
sleep 4

signed="$(count_signed_since "$before")"
stop_bot

if [[ "$signed" -gt 1 ]]; then
  log_result "02-race-duplicate-sign" "VULN_CONFIRMED" "$signed rescue txs — no dedup/idempotency"
elif [[ "$signed" -eq 1 ]]; then
  log_result "02-race-duplicate-sign" "PARTIAL" "only 1 sign — poll interval may be too slow"
else
  log_result "02-race-duplicate-sign" "NO_SIGN" "no signed events"
fi
