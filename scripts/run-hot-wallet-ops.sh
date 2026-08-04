#!/usr/bin/env bash
# Hot wallet ops — read-only deep dive on primary target
# Usage: bash scripts/run-hot-wallet-ops.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export TARGET_WALLET="${TARGET_WALLET:-0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA}"
export WALLETS_FILE="${WALLETS_FILE:-scripts/sandbox/hot-wallet-target.json}"
export WALLETS_ONLY="${WALLETS_ONLY:-1}"
export HEXSTRIKE_MODE="${HEXSTRIKE_MODE:-forensics}"

if [[ -d /opt/drainer-intel ]] || [[ "${HEXSTRIKE_VPS:-}" == "1" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/scripts/forensics-env-vps.sh"
else
  # shellcheck source=/dev/null
  source "$ROOT/scripts/forensics-env-mac.sh"
fi

[[ -f .env ]] && set -a && source .env && set +a

log() { echo "[hot-wallet-ops] $*"; }
failed=0

log "=== HOT WALLET OPS (read-only) ==="
log "Target: $TARGET_WALLET"
log "Wallets file: $WALLETS_FILE"
echo ""

log "Step 1/5 entity-id-pipeline"
python3 scripts/hexstrike-orchestrator.py run entity-id-pipeline --quiet || failed=$((failed + 1))

log "Step 2/5 hot wallet profile + recon"
python3 scripts/hexstrike-orchestrator.py run hot-wallet-ops --quiet || failed=$((failed + 1))

log "Step 3/5 dossier (trace depth 3 + entity)"
python3 scripts/forensics/hot_wallet_dossier.py || failed=$((failed + 1))

log "Step 4/5 mempool sample (120s read-only)"
if [[ -f scripts/autonomous_monitor.py ]]; then
  timeout 125 python3 scripts/autonomous_monitor.py --duration 120 2>/dev/null || log "WARN: monitor timeout/skipped"
else
  log "SKIP monitor"
fi

log "Step 5/5 master report"
python3 scripts/hexstrike-orchestrator.py dispatch Agent-Report-06 generate-vps-master-report 2>/dev/null || \
  python3 scripts/agents/agent_report_vps_master.py || failed=$((failed + 1))

echo ""
if [[ "$failed" -eq 0 ]]; then
  log "DONE — artifacts:"
  log "  artifacts/forensics/hot-wallet-dossier.md"
  log "  artifacts/forensics/hot-wallet-dossier.json"
else
  log "DONE with failures=$failed — check artifacts/orchestrator/"
fi
exit "$failed"
