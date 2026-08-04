#!/usr/bin/env bash
# One-shot: install/update hexstrike-ai on VPS and run all agents to completion.
set -euo pipefail

INSTALL_DIR="${HEXSTRIKE_DIR:-/opt/hexstrike-ai}"
BRANCH="cursor/hexstrike-agents-a1cf"
REPO="https://github.com/Banda198565/hexstrike-ai.git"
SCRIPT_URL="https://raw.githubusercontent.com/Banda198565/hexstrike-ai/${BRANCH}/scripts/vps-orchestrator-bootstrap.sh"

log() { echo "[vps-run-all] $*"; }

[[ $(id -u) -eq 0 ]] || { log "Run as root"; exit 1; }

if [[ ! -x "$INSTALL_DIR/hexstrike-orchestrator" ]]; then
  log "Bootstrap not found — running installer..."
  curl -fsSL "$SCRIPT_URL" | bash
fi

log "Updating repo..."
cd "$INSTALL_DIR"
git remote set-url origin "$REPO" 2>/dev/null || true
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"
chmod +x hexstrike-orchestrator hexstrike-cli scripts/*.sh 2>/dev/null || true

log "Running full agent pipeline..."
./hexstrike-orchestrator run-all

log "Master report:"
if [[ -f artifacts/vps-master-report.json ]]; then
  python3 -c "
import json
r=json.load(open('artifacts/vps-master-report.json'))
print('Host:', r.get('host'))
for h in r.get('highlights',[]): print(' •', h)
print('Artifacts:', ', '.join(r.get('artifacts_present',[])))
"
fi

log "Enable watch service (optional): systemctl enable --now hexstrike-orchestrator"
log "Done. Artifacts in $INSTALL_DIR/artifacts/"
