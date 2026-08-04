#!/usr/bin/env bash
# attack_race.sh — race/duplicate-sign test (Tab 3 of 3-terminal workflow)
#
# Prerequisites (other terminals):
#   Tab 1: anvil --port 8545   OR   ./scripts/sandbox/start-anvil.sh
#   Tab 2: ./scripts/sandbox/run-step1.sh   (or run-step3-defensive.sh for hardening)
#
# LOCAL ANVIL SANDBOX ONLY.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SANDBOX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RPC="${RPC_URL:-http://127.0.0.1:8545}"
LOOPS="${ATTACK_LOOPS:-5}"
LOW_BAL="${ATTACK_LOW_BAL:-300000000000000000}"   # 0.3 ETH (below 0.5 threshold)
HIGH_BAL="${ATTACK_HIGH_BAL:-10000000000000000000}" # 10 ETH

cd "$ROOT"

echo "=== attack_race.sh — balance oscillation race test ==="
echo ""

# --- preflight ---
if ! command -v cast >/dev/null 2>&1; then
  echo "[FAIL] cast not found — install Foundry: foundryup"
  exit 1
fi

if ! curl -sf --max-time 3 "$RPC" \
  -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' >/dev/null; then
  echo "[FAIL] Connection refused at $RPC"
  echo ""
  echo "  Anvil is not running. Open Tab 1 and run ONE of:"
  echo "    anvil --port 8545"
  echo "    ./scripts/sandbox/start-anvil.sh"
  echo ""
  echo "  Then Tab 2: ./scripts/sandbox/run-step1.sh"
  echo "  Then Tab 3: re-run this script"
  exit 1
fi
echo "[OK]   Anvil reachable at $RPC"

ENV_FILE="$("$SANDBOX/resolve-anvil-env.sh" 2>/dev/null || echo "$SANDBOX/anvil.env")"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[FAIL] No anvil.env — run: ./scripts/sandbox/setup-anvil-env.sh"
  exit 1
fi
# shellcheck disable=SC1090
set -a && source "$ENV_FILE" && set +a
BOT="${BOT_ADDRESS:?BOT_ADDRESS missing in anvil.env}"

EVENTS="$ROOT/artifacts/sandbox/dummy-bot-events.jsonl"
before="$(wc -l < "$EVENTS" 2>/dev/null || echo 0)"

echo "[info] Target bot : $BOT"
echo "[info] Loops       : $LOOPS  (low=$LOW_BAL wei → high=$HIGH_BAL wei)"
echo "[info] Events file : $EVENTS (lines before: $before)"
echo ""
echo "Starting attack in 2s — ensure bot is running in Tab 2..."
sleep 2

for i in $(seq 1 "$LOOPS"); do
  echo "--- iteration $i/$LOOPS: drop balance ---"
  "$SANDBOX/set-balance.sh" "$BOT" "$LOW_BAL"
  sleep 3
  echo "--- iteration $i/$LOOPS: restore balance ---"
  "$SANDBOX/set-balance.sh" "$BOT" "$HIGH_BAL"
  sleep 3
done

echo ""
echo "=== Attack complete ==="
echo ""
echo "Read bot events:"
echo "  cat artifacts/sandbox/dummy-bot-events.jsonl"
echo ""
echo "Count signed rescue txs since attack:"
python3 - "$EVENTS" "$before" <<'PY'
import json, sys
path, since = sys.argv[1], int(sys.argv[2])
signed = blocked = triggers = 0
try:
    lines = open(path).read().splitlines()[since:]
except FileNotFoundError:
    print("  (no events file — is bot running in Tab 2?)")
    sys.exit(0)
for line in lines:
    d = json.loads(line)
    if d.get("action") == "trigger":
        triggers += 1
    r = d.get("result")
    if r == "signed":
        signed += 1
    elif r and r.startswith("blocked"):
        blocked += 1
print(f"  triggers : {triggers}")
print(f"  signed   : {signed}")
print(f"  blocked  : {blocked}")
if signed > 1:
    print("\n  ⚠ VULN: multiple rescue txs — no dedup/idempotency")
elif signed == 1:
    print("\n  ✓ single sign (or poll too slow for duplicates)")
elif triggers >= 1:
    print("\n  ? triggers seen but no sign — check DRY_RUN or MIN_GAS")
else:
    print("\n  ? no triggers — bot may not be running or poll interval too slow")
PY

if [[ -f "$ROOT/artifacts/sandbox/anomaly-alerts.jsonl" ]]; then
  echo ""
  echo "Hardening alerts (if Step 3):"
  echo "  cat artifacts/sandbox/anomaly-alerts.jsonl"
fi
