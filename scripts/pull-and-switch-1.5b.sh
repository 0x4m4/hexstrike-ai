#!/usr/bin/env bash
# pull-and-switch-1.5b.sh — stash local Cursor settings, pull, switch to 1.5b
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SETTINGS="$ROOT/.cursor/settings.json"

echo "=== pull-and-switch-1.5b ==="

if [[ -f "$SETTINGS ]] && ! git diff --quiet -- "$SETTINGS" 2>/dev/null; then
  BACKUP="$ROOT/.cursor/settings.json.local.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$SETTINGS" "$BACKUP"
  echo "[OK]   Backed up local settings → $BACKUP"
  git restore "$SETTINGS" 2>/dev/null || git checkout -- "$SETTINGS"
  echo "[OK]   Restored tracked settings for clean pull"
fi

BRANCH="${HEXSTRIKE_BRANCH:-cursor/architecture-manifest-c48c}"
echo "[pull] origin/$BRANCH ..."
git pull origin "$BRANCH"

exec "$ROOT/scripts/switch-to-1.5b.sh"
