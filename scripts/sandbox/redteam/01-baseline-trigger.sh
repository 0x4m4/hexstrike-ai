#!/usr/bin/env bash
# 01-baseline-trigger.sh — verify bot signs rescue on low balance
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"
require_tools

echo "=== REDTEAM 01: baseline trigger ==="
reset_bot_balance
before="$(snapshot_events)"
start_bot_background "HARDENING_ENABLED=false"

"$SANDBOX/set-balance.sh" "$BOT" "$LOW_BAL" >/dev/null
sleep 5

signed="$(count_signed_since "$before")"
stop_bot

if [[ "$signed" -ge 1 ]]; then
  log_result "01-baseline-trigger" "VULN_CONFIRMED" "bot signed $signed rescue tx(s) on low balance"
else
  log_result "01-baseline-trigger" "NO_SIGN" "expected at least 1 signed event"
fi
