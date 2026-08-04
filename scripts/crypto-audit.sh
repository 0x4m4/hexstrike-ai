#!/bin/bash
# E: Local crypto key-surface audit (run on Mac)
set -euo pipefail
ROOT="${CRYPTO_HOME:-$HOME}"
REPORT="${1:-${OUTPUT:-/tmp/crypto-audit-$(date +%Y%m%d-%H%M%S).txt}}"

PROOF_KEY="$HOME/proof-key.txt"
WARN=()

check_proof_key_perms() {
  [[ -e "$PROOF_KEY" ]] || return 0
  local perms
  perms=$(stat -f "%Lp" "$PROOF_KEY" 2>/dev/null || stat -c "%a" "$PROOF_KEY" 2>/dev/null || echo "?")
  echo "proof-key.txt permissions: $perms"
  if [[ "$perms" != "600" && "$perms" != "400" ]]; then
    WARN+=("CRITICAL: proof-key.txt is $perms (world/group readable) — run: chmod 600 $PROOF_KEY")
  fi
}

{
  echo "=== CRYPTO KEY SURFACE AUDIT ==="
  date
  echo "User: $(whoami)"
  echo

  echo "--- Key files ---"
  for f in "$PROOF_KEY" "$HOME/.ethereum/keystore"/* "$HOME/.config/solana/id.json"; do
    [[ -e "$f" || -L "$f" ]] && ls -la "$f" 2>/dev/null
  done
  check_proof_key_perms
  echo

  echo "--- Operator signing scripts (home) ---"
  for f in "$HOME/create-proof-wallet.js" "$HOME/send-proof.js"; do
    [[ -f "$f" ]] && ls -la "$f"
  done
  echo

  echo "--- Symlinks to Eva ---"
  ls -la "$PROOF_KEY" "$HOME/Desktop/redteam" "$HOME/.cursor/skills/geth-wallet-hunt" 2>/dev/null || true
  echo

  echo "--- Grep PRIVATE_KEY (operator paths only, no venv noise) ---"
  GREP_PATHS=()
  for p in "$HOME/Desktop/redteam" "$HOME/create-proof-wallet.js" "$HOME/send-proof.js" "$PROOF_KEY"; do
    [[ -e "$p" ]] && GREP_PATHS+=("$p")
  done
  if ((${#GREP_PATHS[@]})); then
    grep -RIl --exclude-dir={node_modules,.git,Library,Cache,cache,hexstrike-env,virtenv} \
      -E 'PRIVATE_KEY|proof-key|mnemonic|seed phrase' "${GREP_PATHS[@]}" 2>/dev/null | head -30 || true
  else
    echo "(no operator paths found)"
  fi
  echo

  echo "--- Cursor MCP config (no secrets dump) ---"
  [[ -f "$HOME/.cursor/mcp.json" ]] && jq 'walk(if type=="object" and has("env") then .env="[REDACTED]" else . end)' "$HOME/.cursor/mcp.json" 2>/dev/null || echo "no mcp.json"
  echo

  echo "--- npm/pip crypto deps (top) ---"
  pip list 2>/dev/null | grep -iE 'web3|eth|solana|injective|wallet' || true
  echo

  echo "--- Warnings ---"
  if ((${#WARN[@]})); then
    printf '  %s\n' "${WARN[@]}"
  else
    echo "  (none)"
  fi
  echo

  echo "--- Recommendations ---"
  echo "1. proof-key.txt: chmod 600, store on Eva (/Volumes/Eva/secrets/), symlink to ~"
  echo "2. redteam/tools/test-drain-poc.py: quarantine — operator lab only, never third-party treasury"
  echo "3. No signing tools in MCP; no mcp.json env secrets"
  echo "4. pip-audit / npm audit on projects that touch web3"
} | tee "$REPORT"

echo "Saved: $REPORT"
