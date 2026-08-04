#!/usr/bin/env bash
# Mac: принудительно перейти на origin/master когда ветки разошлись
# Usage: bash scripts/mac-fix-checkout.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

log() { echo "[mac-fix] $*"; }
die() { echo "[mac-fix] ERROR: $*" >&2; exit 1; }

log "repo: $ROOT"
log "stash local changes (if any)..."
git stash push -u -m "mac-fix-$(date +%s)" 2>/dev/null || true

log "fetch origin/master..."
git fetch origin master

if ! git show-ref --verify --quiet refs/remotes/origin/master; then
  die "origin/master not found after fetch"
fi

log "reset hard to origin/master..."
git checkout -B master origin/master
git reset --hard origin/master

log "HEAD: $(git log -1 --oneline)"

for f in scripts/forensics-env-mac.sh scripts/run-three-progons.sh scripts/mac-to-vps-sync.sh; do
  [[ -f "$f" ]] || die "missing $f — checkout failed"
done

log "OK — scripts present:"
ls -la scripts/forensics-env-mac.sh scripts/run-three-progons.sh scripts/mac-to-vps-sync.sh

echo ""
echo "Next:"
echo "  export VPS_HOST=78.27.235.70"
echo "  bash scripts/mac-to-vps-sync.sh"
