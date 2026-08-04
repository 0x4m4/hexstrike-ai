#!/usr/bin/env bash
# Изолированное audit-окружение для Mac/Linux (Slither + Mythril).
# Не трогает base conda. Предпочитает Python 3.11 на Mac.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${ROOT}/.venv-audit"

pick_python() {
  if command -v python3.11 &>/dev/null; then
    echo python3.11
    return
  fi
  if [[ "$(uname -s)" == "Darwin" ]] && command -v brew &>/dev/null; then
    if ! command -v python3.11 &>/dev/null; then
      echo "[+] Python 3.11 не найден — ставлю через brew..." >&2
      brew install python@3.11
    fi
    if command -v python3.11 &>/dev/null; then
      echo python3.11
      return
    fi
  fi
  echo python3
}

PY="$(pick_python)"
echo "[+] Project: $ROOT"
echo "[+] Python:  $($PY --version 2>&1)"
echo "[+] Venv:    $VENV"

if [[ -d "$VENV" ]]; then
  echo "[!] Venv уже существует — пересоздать? удалите: rm -rf $VENV"
fi

echo "[+] Creating audit venv..."
"$PY" -m venv "$VENV"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

pip install --upgrade pip wheel setuptools
echo "[+] Installing Slither + Mythril..."
pip install 'slither-analyzer>=0.10,<0.12' 'mythril==0.23.25'

echo ""
echo "[+] Installed versions:"
slither --version || echo "  Slither: not found"
myth version 2>/dev/null || mythril version 2>/dev/null || echo "  Mythril: not found"

cat <<EOF

[+] Audit venv ready.

  Активация:
    source ${VENV}/bin/activate

  Переменные (добавьте в .env или ~/.zshrc):
    export BSCSCAN_API_KEY=your_key
    export ETHERSCAN_API_KEY=\$BSCSCAN_API_KEY
    export BSC_RPC=http://51.222.42.220:8545

  Batch on-chain:
    python3 scripts/run-field-batch.py --targets scripts/sandbox/field-targets-5-batch2.json

  Slither + Mythril:
    ./scripts/run-slither-mythril-audit.sh

  Деактивация:
    deactivate
EOF
