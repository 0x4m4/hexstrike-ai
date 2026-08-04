#!/bin/bash
# Crypto -> Eva (2TB) — Mac one-shot
# Запуск: bash eva-crypto.sh          (перенос)
#         bash eva-crypto.sh --dry-run (только показать что будет)
set -euo pipefail
EVA="/Volumes/Eva"
ROOT="$EVA/HomeOffload/crypto"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1
[[ -d "$EVA" ]] || { echo "Eva не подключена (/Volumes/Eva)"; exit 1; }

mkdir -p "$ROOT"/{redteam/tools,keys,skills,artifacts,reports,scripts,logs}

link_dir() {
  local src="$1" dest="$2"
  mkdir -p "$dest"
  if [[ -L "$src" ]]; then
    echo "[ok] $src -> $(readlink "$src")"
    return 0
  fi
  if [[ -e "$src" ]]; then
    echo "→ $(basename "$src")  ($src -> $dest)"
    [[ $DRY -eq 1 ]] && return 0
    rsync -a "$src/" "$dest/" 2>/dev/null || rsync -a "$src" "$dest/"
    chmod -R u+w "$src" 2>/dev/null || true
    rm -rf "$src" 2>/dev/null || mv "$src" "${src}.bak" && rm -rf "${src}.bak"
    ln -sfn "$dest" "$src"
  elif [[ $DRY -eq 0 ]]; then
    ln -sfn "$dest" "$src"
  else
    echo "[skip] нет $src — создастся symlink после появления данных"
  fi
}

link_file() {
  local src="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  [[ -L "$src" ]] && { echo "[ok] $src"; return 0; }
  [[ -f "$src" ]] || return 0
  echo "→ $(basename "$src")  ($src -> $dest)"
  [[ $DRY -eq 1 ]] && return 0
  mv "$src" "$dest"
  ln -sfn "$dest" "$src"
}

echo "=== Crypto -> $ROOT ==="

# redteam
link_dir "$HOME/Desktop/redteam" "$ROOT/redteam"

# cursor skills
link_dir "$HOME/.cursor/skills/geth-wallet-hunt" "$ROOT/skills/geth-wallet-hunt"
link_dir "$HOME/.cursor/skills/ollama-setup" "$ROOT/skills/ollama-setup" 2>/dev/null || true

# scripts in home
for f in send_proof_tx.py test-drain-poc.py install_hexstrike_vps.sh; do
  [[ -f "$HOME/$f" ]] && link_file "$HOME/$f" "$ROOT/scripts/$f"
done

# key — только перенос, не показывать
[[ -f "$HOME/proof-key.txt" ]] && link_file "$HOME/proof-key.txt" "$ROOT/keys/proof-key.txt" && chmod 600 "$ROOT/keys/proof-key.txt"

# forensics artifacts
mkdir -p "$ROOT/artifacts"
link_dir "$HOME/Desktop/on-chain-forensics" "$ROOT/artifacts/on-chain-forensics" 2>/dev/null || true

# env
if [[ $DRY -eq 0 ]]; then
  grep -q 'CRYPTO_HOME=' "$HOME/.zshrc" 2>/dev/null || cat >> "$HOME/.zshrc" <<ENV

# crypto on Eva
export CRYPTO_HOME="$ROOT"
export HEXSTRIKE_OUTPUT="$ROOT/artifacts/output"
mkdir -p "$ROOT/artifacts/output" "$ROOT/logs"
ENV
  mkdir -p "$ROOT/artifacts/output" "$ROOT/logs"
fi

echo ""
if [[ $DRY -eq 1 ]]; then
  echo "DRY-RUN: повтори без --dry-run для переноса"
  exit 0
fi

echo "ГОТОВО: $ROOT"
ls -la "$ROOT"
echo ""
echo "Проверка symlinks:"
ls -la "$HOME/Desktop/redteam" "$HOME/.cursor/skills/geth-wallet-hunt" 2>/dev/null || true
[[ -L "$HOME/proof-key.txt" ]] && echo "Key: $ROOT/keys/proof-key.txt (chmod 600)"
echo ""
echo "PoC:  python3 ~/Desktop/redteam/tools/test-drain-poc.py"
echo "Hunt: python3 ~/.cursor/skills/geth-wallet-hunt/scripts/check-wallet.py <addr>"
