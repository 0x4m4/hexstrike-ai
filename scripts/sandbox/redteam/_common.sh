#!/usr/bin/env bash
# _common.sh — shared config for local Anvil red-team tests ONLY
set -euo pipefail

REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX="$(cd "$REDTEAM/.." && pwd)"
ROOT="$(cd "$SANDBOX/../.." && pwd)"
RPC="${RPC_URL:-http://127.0.0.1:8545}"
MNEMONIC="${ANVIL_MNEMONIC:-test test test test test test test test test test test junk}"
EVENTS="$ROOT/artifacts/sandbox/dummy-bot-events.jsonl"
ALERTS="$ROOT/artifacts/sandbox/anomaly-alerts.jsonl"
REPORT="$ROOT/artifacts/sandbox/redteam-report.json"

# shellcheck source=/dev/null
source "$SANDBOX/resolve-anvil-env.sh" >/dev/null 2>&1 || true
ENV_FILE="${SANDBOX_ENV:-$("$SANDBOX/resolve-anvil-env.sh")}"
# shellcheck disable=SC1090
set -a && source "$ENV_FILE" && set +a

BOT="${BOT_ADDRESS:?BOT_ADDRESS missing — run setup-anvil-env.sh}"
FUNDER="${FUNDER_ADDRESS:?FUNDER_ADDRESS missing}"
THRESHOLD="${THRESHOLD_WEI:-500000000000000000}"
LOW_BAL="${REDTEAM_LOW_BAL:-300000000000000000}"   # 0.3 ETH
HIGH_BAL="${REDTEAM_HIGH_BAL:-10000000000000000000}" # 10 ETH

ATTACKER_INDEX="${REDTEAM_ATTACKER_INDEX:-2}"
ATTACKER="$(cast wallet address --mnemonic "$MNEMONIC" --mnemonic-index "$ATTACKER_INDEX")"
ATTACKER_KEY="$(cast wallet private-key --mnemonic "$MNEMONIC" --mnemonic-index "$ATTACKER_INDEX")"

require_tools() {
  command -v cast >/dev/null || { echo "[FAIL] cast not found"; exit 1; }
  command -v python3 >/dev/null || { echo "[FAIL] python3 not found"; exit 1; }
  curl -sf --max-time 2 "$RPC" -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' >/dev/null \
    || { echo "[FAIL] Anvil not running at $RPC — run start-anvil.sh"; exit 1; }
}

snapshot_events() {
  wc -l < "$EVENTS" 2>/dev/null || echo 0
}

count_signed_since() {
  local since="$1"
  python3 - "$EVENTS" "$since" <<'PY'
import json, sys
path, since = sys.argv[1], int(sys.argv[2])
n = 0
try:
    lines = open(path).read().splitlines()
except FileNotFoundError:
    print(0); sys.exit(0)
for line in lines[since:]:
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        continue
    if d.get("result") == "signed":
        n += 1
print(n)
PY
}

log_result() {
  local scenario="$1" outcome="$2" detail="${3:-}"
  python3 - "$REPORT" "$scenario" "$outcome" "$detail" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
p = Path(sys.argv[1])
p.parent.mkdir(parents=True, exist_ok=True)
data = {"ts": datetime.now(timezone.utc).isoformat(), "runs": []}
if p.is_file():
    data = json.loads(p.read_text())
data["runs"].append({"scenario": sys.argv[2], "outcome": sys.argv[3], "detail": sys.argv[4]})
p.write_text(json.dumps(data, indent=2) + "\n")
PY
  echo "[RESULT] $scenario → $outcome ${detail:+( $detail )}"
}

start_bot_background() {
  local extra_env="${1:-}"
  # shellcheck disable=SC2086
  env $extra_env POLL_INTERVAL_SEC=2 SANDBOX_ENV="$ENV_FILE" RPC_URL="$RPC" \
    nohup python3 "$SANDBOX/dummy_bot.py" > /tmp/redteam-bot.log 2>&1 &
  echo $! > /tmp/redteam-bot.pid
  sleep 3
  echo "[OK] bot pid $(cat /tmp/redteam-bot.pid)"
}

stop_bot() {
  if [[ -f /tmp/redteam-bot.pid ]]; then
    kill "$(cat /tmp/redteam-bot.pid)" 2>/dev/null || true
    rm -f /tmp/redteam-bot.pid
  fi
}

reset_bot_balance() {
  cast rpc anvil_setBalance "$BOT" "$(python3 -c "print(hex(int('$HIGH_BAL')))")" --rpc-url "$RPC" >/dev/null
}
