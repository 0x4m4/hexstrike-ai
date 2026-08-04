#!/usr/bin/env bash
# vps-fix-cli.sh — restore hexstrike-cli on VPS (run as root on /opt/hexstrike-ai)
set -euo pipefail

INSTALL_DIR="${HEXSTRIKE_DIR:-/opt/hexstrike-ai}"
BRANCH="${HEXSTRIKE_BRANCH:-cursor/hexstrike-agents-a1cf}"
REPO="${HEXSTRIKE_REPO:-https://github.com/Banda198565/hexstrike-ai.git}"

log() { echo "[vps-fix] $*"; }
die() { echo "[vps-fix] ERROR: $*" >&2; exit 1; }

[[ $(id -u) -eq 0 ]] || die "Run as root on VPS"

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  log "No git repo at $INSTALL_DIR — cloning $BRANCH"
  apt-get update -qq && apt-get install -y -qq git python3 curl tmux
  git clone --branch "$BRANCH" --single-branch --depth 1 "$REPO" "$INSTALL_DIR"
else
  log "Updating $INSTALL_DIR → $BRANCH"
  cd "$INSTALL_DIR"
  git fetch origin "$BRANCH"
  git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH"
  git pull origin "$BRANCH"
fi

cd "$INSTALL_DIR"

for f in hexstrike-cli hexstrike-orchestrator hexstrike-ultra; do
  [[ -f "$f" ]] && chmod +x "$f"
done
chmod +x scripts/*.sh 2>/dev/null || true

ln -sf "$INSTALL_DIR/hexstrike-cli" /usr/local/bin/hexstrike-cli
ln -sf "$INSTALL_DIR/hexstrike-orchestrator" /usr/local/bin/hexstrike-orchestrator
ln -sf "$INSTALL_DIR/hexstrike-ultra" /usr/local/bin/hexstrike-ultra

log "HEAD: $(git log -1 --oneline)"
log "hexstrike-cli → $(readlink -f /usr/local/bin/hexstrike-cli)"

echo ""
echo "=== Available commands (NOT scan-lending — use workflows below) ==="
hexstrike-cli --list 2>/dev/null || python3 scripts/hexstrike-agent.py --list

echo ""
echo "=== VPS full readonly recon ==="
echo "  cd $INSTALL_DIR && ./hexstrike-orchestrator run vps-full-readonly"
echo ""
echo "=== Single agent task ==="
echo "  ./hexstrike-orchestrator dispatch Agent-OSINT-03 blockscan-cluster"
echo "  ./hexstrike-cli --agent Agent-OSINT-03 --task entity-resolution"
echo ""
echo "=== Hot wallet target (env) ==="
echo "  export TARGET_WALLET=0x4943f5e7f4e450d48ae82026163ecde8a52c53da"
echo ""
