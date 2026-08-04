#!/usr/bin/env bash
# VPS: запуск ВСЕХ workflows + ВСЕХ agent tasks + forensics + pentest
#
#   bash scripts/vps-run-all-agents.sh              # foreground
#   bash scripts/vps-run-all-agents.sh --background # фон + лог
#   bash scripts/vps-run-all-agents.sh --quick      # без forensics + без field-targets fork
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG_DIR="/var/log/hexstrike"
AGENT_LOG="$LOG_DIR/run-all-agents.log"
mkdir -p "$LOG_DIR" "$ROOT/artifacts/orchestrator/all-agents-run"

QUICK=0
BACKGROUND=0
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    --background) BACKGROUND=1 ;;
  esac
done

run_all() {
  log() { echo "[$(date -u +%H:%M:%S)] $*"; }

  # 1) Server + monitor + orchestrator watch
  log "=== 1/5 vps-start-server ==="
  bash "$ROOT/scripts/vps-start-server.sh" --no-monitor || log "WARN: start-server partial"

  # Monitor отдельно (start-server с --no-monitor выше — запускаем сами)
  pkill -f 'autonomous_monitor.py' 2>/dev/null || true
  sleep 1
  nohup python3 -u "$ROOT/scripts/autonomous_monitor.py" >> "$LOG_DIR/hot-wallet-monitor.log" 2>&1 &
  log "monitor pid $(pgrep -f autonomous_monitor.py | head -1 || echo none)"

  if [[ -f "$ROOT/scripts/forensics-env-vps.sh" ]]; then
    # shellcheck source=/dev/null
    source "$ROOT/scripts/forensics-env-vps.sh"
  fi

  ORCH="python3 $ROOT/scripts/hexstrike-orchestrator.py"
  FAILED=0

  # 2) All orchestrator workflows
  log "=== 2/5 all workflows ==="
  WORKFLOWS=(
    infra-passive
    defensive-disclosure
    entity-id-pipeline
    full-recon-readonly
    vps-full-readonly
    hot-wallet-ops
    operator-lab
    trx-drainer-forensics
    evm-drainer-forensics
    apeterminal-forensics
    solana-drainer-forensics
    vanilla-drainer-forensics
    permit-farming-forensics
    create2-forensics
  )
  if [[ "$QUICK" -eq 0 ]]; then
    WORKFLOWS+=(
      field-targets-5
      multi-wallet-conclusions
      operator-targets-3progon
    )
  fi

  for wf in "${WORKFLOWS[@]}"; do
    log "workflow: $wf"
    if $ORCH run "$wf" --quiet >> "$LOG_DIR/wf-${wf}.log" 2>&1; then
      log "  OK $wf"
    else
      log "  FAIL $wf (see $LOG_DIR/wf-${wf}.log)"
      FAILED=$((FAILED + 1))
    fi
  done

  # 3) Every agent task (registry dispatch)
  log "=== 3/5 dispatch all agent tasks ==="
  if python3 "$ROOT/scripts/vps-dispatch-all-agents.py" >> "$LOG_DIR/dispatch-all.log" 2>&1; then
    log "  OK all agent dispatches"
  else
    log "  WARN some agent dispatches failed — artifacts/orchestrator/all-agents-run/summary.json"
    FAILED=$((FAILED + 1))
  fi

  # 4) Web pentest + hot wallet dossier
  log "=== 4/5 web pentest + dossier ==="
  bash "$ROOT/scripts/run-web-app-pentest.sh" >> "$LOG_DIR/web-pentest.log" 2>&1 || FAILED=$((FAILED + 1))
  python3 "$ROOT/scripts/forensics/hot_wallet_dossier.py" >> "$LOG_DIR/hot-wallet-dossier.log" 2>&1 || true
  bash "$ROOT/scripts/run-payroll-otc-close.sh" >> "$LOG_DIR/payroll.log" 2>&1 || true

  # 5) Master report
  log "=== 5/5 master report ==="
  $ORCH dispatch Agent-Report-06 generate-vps-master-report --quiet >> "$LOG_DIR/master-report.log" 2>&1 || true

  log "=== DONE failed_workflows_or_batches=$FAILED ==="
  log "Reports:"
  log "  artifacts/vps-master-report.json"
  log "  artifacts/orchestrator/all-agents-run/summary.json"
  log "  artifacts/orchestrator/latest.json"
  echo "$FAILED" > "$ROOT/artifacts/.vps-all-agents-failed"
}

if [[ "$BACKGROUND" -eq 1 ]]; then
  echo "Background log: $AGENT_LOG"
  nohup bash -c "$(declare -f run_all); run_all" >> "$AGENT_LOG" 2>&1 &
  echo "PID $! — tail -f $AGENT_LOG"
else
  run_all
fi
