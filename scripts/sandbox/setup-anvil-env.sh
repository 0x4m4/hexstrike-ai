#!/usr/bin/env bash
# setup-anvil-env.sh — create gitignored anvil.env with Foundry public test keys
set -euo pipefail

SANDBOX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$SANDBOX/anvil.env"
EXAMPLE="$SANDBOX/anvil.env.example"
MNEMONIC="${ANVIL_MNEMONIC:-test test test test test test test test test test test junk}"
BOT_INDEX="${ANVIL_BOT_INDEX:-1}"
FUNDER_INDEX="${ANVIL_FUNDER_INDEX:-0}"

if [[ -f "$OUT" ]]; then
  echo "[OK]   $OUT already exists (not overwritten)"
  echo "       Delete and re-run to regenerate: rm $OUT && $0"
  exit 0
fi

if ! command -v cast >/dev/null 2>&1; then
  echo "[FAIL] cast not found — install Foundry first"
  exit 1
fi

BOT_ADDRESS="$(cast wallet address --mnemonic "$MNEMONIC" --mnemonic-index "$BOT_INDEX")"
BOT_PRIVATE_KEY="$(cast wallet private-key --mnemonic "$MNEMONIC" --mnemonic-index "$BOT_INDEX")"
FUNDER_ADDRESS="$(cast wallet address --mnemonic "$MNEMONIC" --mnemonic-index "$FUNDER_INDEX")"

cat >"$OUT" <<ENV
# LOCAL SANDBOX ONLY — Anvil public test keys. Never use in production.
RPC_URL=http://127.0.0.1:8545
UPSTREAM_RPC=http://127.0.0.1:8545
PROXY_PORT=8546
CHAIN_ID=31337

BOT_ADDRESS=${BOT_ADDRESS}
BOT_PRIVATE_KEY=${BOT_PRIVATE_KEY}
FUNDER_ADDRESS=${FUNDER_ADDRESS}

THRESHOLD_WEI=500000000000000000
MIN_GAS_WEI=10000000000000000
RESCUE_VALUE_WEI=1000000000000000
POLL_INTERVAL_SEC=10

HARDENING_ENABLED=false
GO_LIVE_GATES=false
ALLOWED_FUNDERS=${FUNDER_ADDRESS}
ALLOWED_DESTINATIONS=${FUNDER_ADDRESS}
DIRECT_RPC_URL=http://127.0.0.1:8545
QUORUM_RPC_URLS=http://127.0.0.1:8545
QUORUM_MIN_AGREE=1
MAX_BALANCE_DELTA_WEI=0
ANOMALY_STALE_TIMEOUT_SEC=120
GUARD_RPC_TIMEOUT_SEC=10
ENV

echo "[OK]   Created $OUT (gitignored)"
echo "       BOT_ADDRESS=$BOT_ADDRESS"
echo "       Template reference: $EXAMPLE"
