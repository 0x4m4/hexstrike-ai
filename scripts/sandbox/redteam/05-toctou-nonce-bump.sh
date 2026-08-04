#!/usr/bin/env bash
# 05-toctou-nonce-bump.sh — bump bot nonce while trigger pending
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"
require_tools

echo "=== REDTEAM 05: TOCTOU nonce bump ==="
reset_bot_balance
before="$(snapshot_events)"

# Bot key sends a self-tx to consume nonce right when balance drops
start_bot_background "HARDENING_ENABLED=false POLL_INTERVAL_SEC=1"
"$SANDBOX/set-balance.sh" "$BOT" "$LOW_BAL" >/dev/null

# Parallel nonce bump from bot wallet (simulates concurrent tx)
cast send "$BOT" --private-key "$(grep BOT_PRIVATE_KEY "$ENV_FILE" | cut -d= -f2)" \
  --value 1 --rpc-url "$RPC" >/dev/null 2>&1 || true

sleep 6
signed="$(count_signed_since "$before")"
errors="$(python3 - "$EVENTS" "$before" <<'PY'
import json, sys
path, since = sys.argv[1], int(sys.argv[2])
n = 0
for line in open(path).read().splitlines()[since:]:
    d = json.loads(line)
    if d.get("result") == "error":
        n += 1
print(n)
PY
)"
stop_bot
reset_bot_balance

if [[ "$errors" -ge 1 ]]; then
  log_result "05-toctou-nonce-bump" "DEFENDED" "bot got error on stale nonce ($errors errors)"
elif [[ "$signed" -ge 1 ]]; then
  log_result "05-toctou-nonce-bump" "VULN_CONFIRMED" "bot signed despite nonce race"
else
  log_result "05-toctou-nonce-bump" "INCONCLUSIVE" "signed=$signed errors=$errors"
fi
