#!/usr/bin/env bash
# set-balance.sh — tweak Anvil account balance for sandbox tests (anvil_setBalance)
set -euo pipefail

RPC="${RPC_URL:-http://127.0.0.1:8545}"
ADDR="${1:-}"
WEI="${2:-}"

if [[ -z "$ADDR" || -z "$WEI" ]]; then
  echo "Usage: $0 <address> <balance_wei>"
  echo "Example (drop bot to 0.3 ETH):"
  echo "  $0 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 300000000000000000"
  exit 1
fi

if ! command -v cast >/dev/null 2>&1; then
  echo "[FAIL] cast not found — install Foundry"
  exit 1
fi

HEX_WEI=$(python3 -c "print(hex(int('$WEI')))")
cast rpc anvil_setBalance "$ADDR" "$HEX_WEI" --rpc-url "$RPC"
NEW=$(cast balance "$ADDR" --rpc-url "$RPC")
echo "[OK] $ADDR balance now: $NEW wei"
