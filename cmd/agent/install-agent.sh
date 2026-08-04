#!/usr/bin/env bash
# install-agent.sh — install HexStrike agent globally or to local bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Installing HexStrike Agent..."
echo ""

bash "$SCRIPT_DIR/build.sh"

AGENT_BIN="$PROJECT_ROOT/bin/hexstrike-agent"

if [[ "${1:-}" == "global" ]]; then
  echo ""
  echo "[*] Installing to /usr/local/bin..."
  install -m 755 "$AGENT_BIN" /usr/local/bin/hexstrike-agent
  echo "[OK] Installed globally: hexstrike-agent"
else
  echo ""
  echo "[OK] Installed locally: $AGENT_BIN"
  echo ""
  echo "To add to PATH, run:"
  echo "  export PATH=\"\$PATH:$PROJECT_ROOT/bin\""
  echo ""
  echo "Or install globally:"
  echo "  bash $SCRIPT_DIR/install-agent.sh global"
fi
