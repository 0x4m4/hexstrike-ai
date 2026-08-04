#!/usr/bin/env bash
# VPS: after Mac rsync — load env, verify drainer paths, run 3 progons
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

log() { echo "[vps-post-sync] $*"; }

mkdir -p /opt/drainer-intel /var/log/hexstrike
chmod +x scripts/*.sh 2>/dev/null || true

if [[ -f hexstrike_env/bin/activate ]]; then
  # shellcheck source=/dev/null
  source hexstrike_env/bin/activate
elif [[ -f hexstrike-env/bin/activate ]]; then
  # shellcheck source=/dev/null
  source hexstrike-env/bin/activate
fi

# shellcheck source=/dev/null
source "$ROOT/scripts/forensics-env-vps.sh"

if [[ -f .env ]]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

log "Drainer paths:"
log "  TRX:    ${TRX_DRAINER_REPO} ($([[ -d ${TRX_DRAINER_REPO} ]] && echo OK || echo MISSING))"
log "  EVM:    ${EVM_DRAINER_REPO} ($([[ -d ${EVM_DRAINER_REPO} ]] && echo OK || echo MISSING))"
log "  Ape:    ${APETERMINAL_REPO} ($([[ -d ${APETERMINAL_REPO} ]] && echo OK || echo MISSING))"
log "  Solana: ${SOLANA_DRAINER_REPO} ($([[ -d ${SOLANA_DRAINER_REPO} ]] && echo OK || echo MISSING))"

log "API keys:"
[[ -n "${ARKHAM_API_KEY:-}" ]] && log "  ARKHAM_API_KEY: set" || log "  ARKHAM_API_KEY: MISSING"
[[ -n "${GETBLOCK_API_KEY:-}" ]] && log "  GETBLOCK_API_KEY: set" || log "  GETBLOCK_API_KEY: MISSING"
[[ -n "${GITHUB_TOKEN:-}" ]] && log "  GITHUB_TOKEN: set" || log "  GITHUB_TOKEN: optional (not set)"

log "Running 3 progons..."
bash scripts/run-three-progons.sh 2>&1 | tee -a /var/log/hexstrike/progons-$(date +%Y%m%d-%H%M%S).log

log "IOC files: $(ls -1 artifacts/*-iocs.json 2>/dev/null | wc -l)"
log "Reports:   $(ls -1 artifacts/forensics/*-report.json 2>/dev/null | wc -l)"

systemctl restart hexstrike-orchestrator hexstrike-server 2>/dev/null || true
log "Done."
