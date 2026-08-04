#!/usr/bin/env bash
# Bootstrap Dual-Mode contract audit toolchain (defense + sandbox offense).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> HexStrike Dual-Mode toolchain bootstrap"

install_python_tools() {
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --user -q slither-analyzer mythril 2>/dev/null || true
  fi
}

install_foundry() {
  if command -v forge >/dev/null 2>&1; then
    echo "Foundry already installed: $(forge --version | head -1)"
    return
  fi
  if [[ -x "$HOME/.foundry/bin/forge" ]]; then
    export PATH="$HOME/.foundry/bin:$PATH"
    return
  fi
  echo "Installing Foundry..."
  curl -fsSL https://foundry.paradigm.xyz | bash
  # shellcheck source=/dev/null
  source "$HOME/.foundry/bin/foundryup" 2>/dev/null || "$HOME/.foundry/bin/foundryup"
}

install_python_tools
install_foundry

echo ""
echo "Detected tools:"
python3 - <<'PY'
import json, sys
sys.path.insert(0, "src")
from hexstrike.skills.contract_toolchain import ContractToolchain
print(json.dumps(ContractToolchain().detect_tools(), indent=2))
PY

echo ""
echo "Run defense audit:"
echo "  ./hexstrike-orchestrator run dual-mode-defense"
echo ""
echo "Run sandbox offense (requires HEXSTRIKE_SANDBOX=1):"
echo "  HEXSTRIKE_SANDBOX=1 ./hexstrike-orchestrator run dual-mode-offense"
echo ""
echo "Direct CLI:"
echo "  python3 hexstrike_orchestrator.py dual-mode scripts/sandbox/contracts/RevertOnWithdraw.sol --mode defense"
