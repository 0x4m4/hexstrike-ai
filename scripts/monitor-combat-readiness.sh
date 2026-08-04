#!/usr/bin/env bash
# Combat-readiness verification for autonomous_monitor.py
# Confirms: RPC/mempool, heartbeat, IR trigger logic, block fallback, state persistence.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET_WALLET="${TARGET_WALLET:-0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA}"
RPC_URL="${RPC_URL:-http://51.222.42.220:8545}"
SAMPLE_SEC="${MONITOR_READINESS_SAMPLE_SEC:-45}"
HEARTBEAT_POLLS="${MONITOR_HEARTBEAT_POLLS:-30}"
LOG_FILE="${MONITOR_READINESS_LOG:-/tmp/hexstrike-readiness-$$.log}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass=0
fail=0
warn=0

ok()   { echo -e "${GREEN}PASS${NC}: $*"; pass=$((pass + 1)); }
bad()  { echo -e "${RED}FAIL${NC}: $*"; fail=$((fail + 1)); }
note() { echo -e "${YELLOW}WARN${NC}: $*"; warn=$((warn + 1)); }

monitor_procs() {
  ps aux 2>/dev/null | grep '[a]utonomous_monitor.py' || true
}

monitor_count() {
  monitor_procs | wc -l | tr -d ' '
}

echo "=== HexStrike Monitor Combat Readiness ==="
echo "Target: $TARGET_WALLET"
echo "RPC:    $RPC_URL"
echo ""

# 1. RPC alive
if curl -sf --max-time 8 -X POST "$RPC_URL" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  | grep -q '"result"'; then
  ok "RPC eth_blockNumber"
else
  bad "RPC unreachable or invalid response"
fi

# 2. Mempool (txpool) — critical for pending outflow
if curl -sf --max-time 12 -X POST "$RPC_URL" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"txpool_content","params":[],"id":1}' \
  | grep -q '"pending"'; then
  ok "txpool_content (mempool pending) available"
else
  note "txpool_content unavailable — monitor falls back to block scan only (Flashbots/private txs invisible in mempool anyway)"
fi

# 3. Block fetch (Flashbots fallback path)
if curl -sf --max-time 8 -X POST "$RPC_URL" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["latest", true],"id":1}' \
  | grep -q '"transactions"'; then
  ok "eth_getBlockByNumber latest (block-level fallback)"
else
  bad "Cannot fetch latest block with txs"
fi

# 4. IR trigger unit test (no network)
echo ""
echo "--- IR trigger logic (offline) ---"
python3 << 'PY'
import sys
sys.path.insert(0, "scripts")
from autonomous_monitor import is_hot_wallet_outflow, HOT_WALLET

hw = HOT_WALLET.lower()
cases = [
    ({"from": hw, "to": "0xdead", "value": "0x1", "hash": "0xa"}, True, "EOA outflow"),
    ({"from": "0xother", "to": hw, "value": "0x1", "hash": "0xb"}, False, "inflow ignored"),
    ({"from": hw, "to": hw, "value": "0x0", "hash": "0xc"}, False, "self zero-value ignored"),
    ({"from": hw, "to": "0xdead", "value": "0x0", "input": "0x", "hash": "0xd"}, False, "zero outflow ignored"),
    ({"from": hw, "to": "0xdead", "value": "0x0", "input": "0x" + "a"*64, "hash": "0xe"}, True, "contract call from hot wallet"),
]
for tx, expect, label in cases:
    got = is_hot_wallet_outflow(tx)
    assert got == expect, f"{label}: expected {expect}, got {got}"
print("IR trigger cases: OK")
PY
ok "is_hot_wallet_outflow() — from-only EOA + contract calls"

# 5. Sample live monitor run (--duration exits cleanly; no GNU timeout needed for macOS)
echo ""
echo "--- Live sample (${SAMPLE_SEC}s) ---"
export TARGET_WALLET RPC_URL MONITOR_HEARTBEAT_POLLS="$HEARTBEAT_POLLS"
export MONITOR_BLOCK_SCAN_POLLS=5
python3 -u scripts/autonomous_monitor.py \
  --duration "$SAMPLE_SEC" \
  > "$LOG_FILE" 2>&1 || true

if [[ ! -s "$LOG_FILE" ]]; then
  bad "Sample log empty — run: python3 -u scripts/autonomous_monitor.py --duration 15"
elif grep -qi '\[heartbeat\]' "$LOG_FILE"; then
  ok "Heartbeat lines in sample log"
  grep -i '\[heartbeat\]' "$LOG_FILE" | tail -1
else
  note "No heartbeat in sample — check RPC or increase MONITOR_READINESS_SAMPLE_SEC"
fi

if grep -qi '\[heartbeat\].*pending_txs=' "$LOG_FILE"; then
  ok "Mempool polling active (pending_txs in heartbeat)"
elif grep -qi '\[monitor\] RPC primary' "$LOG_FILE"; then
  note "Monitor started but no heartbeat — git pull master (728e059+) for heartbeat support"
  bad "No mempool polling activity in sample log"
else
  bad "No mempool polling activity in sample log"
fi

if grep -qi 'block-scan every\|\[block-scan\]' "$LOG_FILE"; then
  ok "Block-level fallback configured or executed"
else
  note "Block fallback log not seen (runs every MONITOR_BLOCK_SCAN_POLLS; silent on success)"
fi

# 6. State file
STATE="artifacts/monitor/autonomous_state.json"
if [[ -f "$STATE" ]]; then
  ok "autonomous_state.json exists"
  python3 -c "
import json
s=json.load(open('$STATE'))
for k in ('last_poll', 'seen_hashes', 'rpc'):
    assert k in s, f'missing {k}'
seen = len(s.get('seen_hashes', []))
print(f\"  last_poll={s['last_poll']} seen_hashes={seen} rpc={s.get('rpc','?')[:30]}...\")
"
else
  note "autonomous_state.json not created yet (appears after 10 polls in sample run)"
fi

# 7. Risk-zone documentation
echo ""
echo "--- Risk zones (manual / architectural) ---"
note "Smart wallet/proxy: monitor matches tx.from==hot_wallet only (EOA OK for 0x4943...)"
note "Flashbots/private mempool: invisible to txpool — block scan every MONITOR_BLOCK_SCAN_POLLS mitigates latency"
note "Mempool reorg (tx disappears): seen_hashes suppresses duplicate alerts; no false IR on vanish"
note "Rescue owner: NOT auto-fired — operator must run IR per INCIDENT-CONCLUSION.md"

# 8. Production process check (ps-based — works on Linux and macOS)
echo ""
echo "--- Production process ---"
inst=$(monitor_count)
if [[ "$inst" -gt 0 ]]; then
  ok "autonomous_monitor.py process running (${inst} instance(s))"
  monitor_procs | head -3
  if [[ "$inst" -gt 1 ]]; then
    bad "Multiple monitor instances — kill duplicates (pkill -f autonomous_monitor.py; restart one)"
  fi
else
  note "No production monitor process (start after readiness PASS)"
fi

# Summary
echo ""
echo "============================================"
echo -e "Result: ${GREEN}$pass PASS${NC} | ${RED}$fail FAIL${NC} | ${YELLOW}$warn WARN${NC}"
if [[ "$fail" -eq 0 ]]; then
  echo -e "${GREEN}COMBAT READY${NC} (pending IR = operator action on HOT_WALLET_OUTFLOW alert)"
  exit 0
else
  echo -e "${RED}NOT COMBAT READY${NC} — fix FAIL items before relying on monitor"
  exit 1
fi
