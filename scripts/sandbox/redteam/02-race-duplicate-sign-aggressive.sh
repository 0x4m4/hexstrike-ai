#!/usr/bin/env bash
# 02-race-duplicate-sign-aggressive.sh — aggressive race/duplicate-sign stress test (LOCAL ANVIL ONLY)
# Rapidly oscillates the bot balance using many concurrent anvil_setBalance calls to force duplicate triggers.
# WARNING: local sandbox only. Do NOT run against remote nodes.
set -euo pipefail

REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX="$(cd "$REDTEAM/.." && pwd)"
ROOT="$(cd "$SANDBOX/../.." && pwd)"
# load common env helpers
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"
require_tools

# Aggressive defaults (override via env)
LOOPS=${AGGRESSIVE_LOOPS:-50}          # outer iterations
PARALLEL=${AGGRESSIVE_PARALLEL:-20}    # concurrent set-balance calls per phase
PAUSE_BETWEEN_PHASES=${AGGRESSIVE_PHASE_PAUSE:-0.05} # seconds between low/high bursts
RPC_CALL="cast rpc anvil_setBalance"

EVENTS="$ROOT/artifacts/sandbox/dummy-bot-events.jsonl"
before="$(snapshot_events)"

echo "=== AGGRESSIVE RACE TEST ==="
echo "Target bot: $BOT"
echo "Loops: $LOOPS, Parallel per phase: $PARALLEL"

echo "Starting bot (fast poll) ..."
start_bot_background "HARDENING_ENABLED=false POLL_INTERVAL_SEC=1"

# helper to hex a decimal value
hex() { python3 - <<PY
import sys
print(hex(int(sys.stdin.read().strip())))
PY
}

LOW_HEX=$(printf "%s" "$LOW_BAL" | hex)
HIGH_HEX=$(printf "%s" "$HIGH_BAL" | hex)

# Run many rapid low->high bursts in parallel to maximize race windows
for ((i=1;i<=LOOPS;i++)); do
  echo "[iter $i/$LOOPS] spawning low-bursts ..."
  for ((p=1;p<=PARALLEL;p++)); do
    $RPC_CALL "$BOT" "$LOW_HEX" --rpc-url "$RPC" &
  done
  sleep "$PAUSE_BETWEEN_PHASES"
  echo "[iter $i/$LOOPS] spawning high-bursts ..."
  for ((p=1;p<=PARALLEL;p++)); do
    $RPC_CALL "$BOT" "$HIGH_HEX" --rpc-url "$RPC" &
  done
  # small jitter between iterations to avoid lockstep scheduling
  sleep 0.02
done

# wait for background RPC calls to finish
wait || true

# give bot a short grace period to process triggers
sleep 3

signed=$(count_signed_since "$before")
stop_bot

echo "=== AGGRESSIVE TEST COMPLETE ==="
echo "Signed rescue txs during attack: $signed"
if [[ "$signed" -gt 1 ]]; then
  echo "⚠ VULN: multiple rescue txs detected — no dedup/idempotency"
else
  echo "OK: single or no sign observed (signed=$signed)"
fi

echo "Check events: cat $EVENTS"
