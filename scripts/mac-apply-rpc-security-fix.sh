#!/usr/bin/env bash
# Mac: clone/pull HexStrike and apply RPC security fix branch.
# Usage (from anywhere):
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/Banda198565/hexstrike-ai/cursor/check-cursor-agent-script-a59e/scripts/mac-apply-rpc-security-fix.sh)"
# Or if repo already exists:
#   cd ~/hexstrike-ai && bash scripts/mac-apply-rpc-security-fix.sh
set -euo pipefail

REPO_URL="${HEXSTRIKE_REPO_URL:-https://github.com/Banda198565/hexstrike-ai.git}"
BRANCH="${HEXSTRIKE_BRANCH:-cursor/check-cursor-agent-script-a59e}"
INSTALL_DIR="${HEXSTRIKE_HOME:-$HOME/hexstrike-ai}"

log() { echo "[mac-rpc-fix] $*"; }
die() { echo "[mac-rpc-fix] ERROR: $*" >&2; exit 1; }

if [[ -d "$INSTALL_DIR/.git" ]]; then
  log "Using existing repo: $INSTALL_DIR"
  cd "$INSTALL_DIR"
else
  log "Cloning to $INSTALL_DIR ..."
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

log "Fetch branch $BRANCH ..."
git fetch origin "$BRANCH"
git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH"
git pull origin "$BRANCH" 2>/dev/null || true

CFG="config/rpc_config.json"
[[ -f "$CFG" ]] || die "$CFG missing — wrong directory? pwd=$(pwd)"

log "=== RPC config ==="
python3 - <<'PY'
import json
c = json.load(open("config/rpc_config.json"))
print("primary:", c.get("primary"))
print("fallbacks:", c.get("fallbacks"))
removed = c.get("removed_endpoints", [])
print("removed_endpoints:", len(removed))
for r in removed:
    print("  -", r.get("url"), "|", r.get("reason", "")[:60])
bad = ["45.33.17.6", "173.255.192.47"]
fb = json.dumps(c.get("fallbacks", []))
if any(b in fb for b in bad):
    raise SystemExit("FAIL: dangerous fallbacks still in config")
print("OK: critical fallbacks absent from active list")
PY

log "Done. Repo: $(pwd)"
log "Verify: python3 -c \"import json; print(json.load(open('config/rpc_config.json'))['fallbacks'])\""
