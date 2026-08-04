#!/usr/bin/env bash
# Mac → VPS: checkout master, sync Eva drainer repos + artifacts, trigger VPS run
#
# Usage:
#   export VPS_HOST=78.27.235.70
#   export VPS_USER=root
#   bash scripts/mac-to-vps-sync.sh
#
# Optional: VPS_SSH_KEY=~/.ssh/id_ed25519  (preferred over password)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VPS_HOST="${VPS_HOST:-78.27.235.70}"
VPS_USER="${VPS_USER:-root}"
VPS_INSTALL="${VPS_INSTALL:-/opt/hexstrike-ai}"
EVA_STORAGE="${EVA_STORAGE:-/Volumes/Eva/mufasaai-storage}"
DRAINER_INTEL="${VPS_DRAINER_INTEL:-/opt/drainer-intel}"

RSYNC_SSH=(ssh -o StrictHostKeyChecking=accept-new)
if [[ -n "${VPS_SSH_KEY:-}" && -f "$VPS_SSH_KEY" ]]; then
  RSYNC_SSH=(ssh -i "$VPS_SSH_KEY" -o StrictHostKeyChecking=accept-new)
fi

log() { echo "[mac-sync] $*"; }
die() { echo "[mac-sync] ERROR: $*" >&2; exit 1; }

[[ -d "$EVA_STORAGE" ]] || die "Eva not mounted: $EVA_STORAGE"

log "=== Step 1/4: git checkout master ==="
git stash push -m "mac-sync-$(date +%s)" -- agents/workflows.json 2>/dev/null || true
git fetch origin master
git checkout master
git pull origin master --rebase || git reset --hard origin/master
log "HEAD: $(git log -1 --oneline)"

log "=== Step 2/4: local forensics (Eva repos) ==="
# shellcheck source=/dev/null
source "$ROOT/scripts/forensics-env-mac.sh"
bash "$ROOT/scripts/run-all-forensics.sh"

log "=== Step 3/4: rsync drainer repos + artifacts → VPS ==="
REMOTE="${VPS_USER}@${VPS_HOST}"

for repo in TRX-Drainer-Tool evm-drainer apeterminal-main Solana-Drainer-Tool; do
  src="${EVA_STORAGE}/${repo}"
  [[ -d "$src" ]] || { log "WARN: skip missing $src"; continue; }
  log "rsync $repo"
  rsync -avz --delete -e "${RSYNC_SSH[*]}" \
    "$src/" "${REMOTE}:${DRAINER_INTEL}/${repo}/"
done

log "rsync artifacts/"
rsync -avz -e "${RSYNC_SSH[*]}" \
  "$ROOT/artifacts/" "${REMOTE}:${VPS_INSTALL}/artifacts/"

log "rsync repo scripts (master)"
rsync -avz -e "${RSYNC_SSH[*]}" \
  --exclude '.git' --exclude 'hexstrike_env' --exclude 'hexstrike-env' \
  "$ROOT/" "${REMOTE}:${VPS_INSTALL}/"

log "=== Step 4/4: VPS post-sync run ==="
"${RSYNC_SSH[@]}" "${REMOTE}" "bash ${VPS_INSTALL}/scripts/vps-post-sync.sh"

log "=== DONE ==="
log "Reports: ssh ${REMOTE} 'ls -la ${VPS_INSTALL}/artifacts/forensics/session-report-*.md'"
