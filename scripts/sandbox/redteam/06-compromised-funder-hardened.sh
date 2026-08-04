#!/usr/bin/env bash
# 06-compromised-funder-hardened.sh — attack #06 with GO-LIVE gates + allowlist (must NOT sign)
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"
require_tools

echo "=== REDTEAM 06 (hardened): compromised FUNDER + allowlist ==="
reset_bot_balance
before="$(snapshot_events)"

# Legitimate funder on allowlist; attacker substituted as FUNDER_ADDRESS
start_bot_background "HARDENING_ENABLED=true GO_LIVE_GATES=true ALLOWED_FUNDERS=$FUNDER ALLOWED_DESTINATIONS=$FUNDER FUNDER_ADDRESS=$ATTACKER"
"$SANDBOX/set-balance.sh" "$BOT" "$LOW_BAL" >/dev/null
sleep 6
signed="$(count_signed_since "$before")"
blocked="$(python3 - "$EVENTS" "$before" <<'PY'
import json, sys
path, since = sys.argv[1], int(sys.argv[2])
n = 0
try:
    lines = open(path).read().splitlines()
except FileNotFoundError:
    print(0); sys.exit(0)
for line in lines[since:]:
    d = json.loads(line)
    r = str(d.get("result", ""))
    g = str(d.get("guard_event", ""))
    if r.startswith("blocked_") or r == "BLOCK_COMPROMISED_FUNDER" or g == "BLOCK_COMPROMISED_FUNDER":
        n += 1
print(n)
PY
)"
stop_bot
reset_bot_balance

if [[ "$signed" -ge 1 ]]; then
  log_result "06-compromised-funder-hardened" "VULN_CONFIRMED" "signed=$signed with compromised funder despite allowlist"
elif [[ "$blocked" -ge 1 ]]; then
  log_result "06-compromised-funder-hardened" "DEFENDED" "allowlist blocked compromised FUNDER ($blocked blocks)"
else
  log_result "06-compromised-funder-hardened" "INCONCLUSIVE" "signed=$signed blocked=$blocked"
fi
