#!/usr/bin/env bash
# HexStrike — запуск ПО ЦЕЛИ (preventive IR, hot wallet 0x4943..., не full noise)
#
# Цель: pending outflow виден до confirmation; forensics closed; Jenkins hardening intel.
#
# Server:
#   cd /opt/hexstrike-ai && git pull origin master
#   bash scripts/vps-run-by-goal.sh
#   bash scripts/vps-run-by-goal.sh --background
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -w /var/log/hexstrike ]] 2>/dev/null || [[ $(id -u) -eq 0 ]]; then
  LOG_DIR="/var/log/hexstrike"
else
  LOG_DIR="$ROOT/artifacts/goal-run/logs"
fi
mkdir -p "$LOG_DIR" "$ROOT/artifacts/goal-run"
GOAL_LOG="$LOG_DIR/goal-run.log"
TARGET_WALLET="${TARGET_WALLET:-0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA}"
JENKINS="${JENKINS_TARGET:-http://51.250.97.223:8080}"

BACKGROUND=0
for arg in "$@"; do [[ "$arg" == "--background" ]] && BACKGROUND=1; done

run_goal() {
  log() { echo "[goal $(date -u +%H:%M:%S)] $*" | tee -a "$GOAL_LOG"; }
  ORCH="python3 $ROOT/scripts/hexstrike-orchestrator.py"
  FAIL=0

  log "══════════════════════════════════════════════════════"
  log " GOAL: Preventive IR — hot wallet $TARGET_WALLET"
  log " Forensics CLOSED | Withdrawal NOT occurred | Monitor COMBAT"
  log "══════════════════════════════════════════════════════"

  # ── P0: API + Monitor (единственное окно IR) ─────────────────
  log ""
  log "▶ P0: hexstrike-server + autonomous_monitor"
  if [[ $(id -u) -eq 0 ]] && [[ -x "$ROOT/scripts/vps-start-server.sh" ]]; then
    bash "$ROOT/scripts/vps-start-server.sh" 2>&1 | tee -a "$GOAL_LOG" || { log "P0 server: FAIL"; FAIL=$((FAIL + 1)); }
  else
    if curl -sf --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1; then
      log "P0 server: already up :8888"
    elif [[ -f "$ROOT/hexstrike_env/bin/python3" ]]; then
      nohup "$ROOT/hexstrike_env/bin/python3" "$ROOT/hexstrike_server.py" --port 8888 >> "$LOG_DIR/hexstrike-server.log" 2>&1 &
      sleep 3
      curl -sf http://127.0.0.1:8888/health >/dev/null && log "P0 server: started" || { log "P0 server: FAIL"; FAIL=$((FAIL + 1)); }
    else
      log "P0 server: skip (run vps-start-server.sh on VPS as root)"
    fi
  fi

  export MONITOR_HEARTBEAT_POLLS=5 MONITOR_READINESS_SAMPLE_SEC=20
  if bash "$ROOT/scripts/monitor-combat-readiness.sh" 2>&1 | tee -a "$GOAL_LOG"; then
    log "P0 monitor readiness: COMBAT READY"
    if ! pgrep -f 'autonomous_monitor.py' >/dev/null 2>&1; then
      nohup python3 -u "$ROOT/scripts/autonomous_monitor.py" >> "$LOG_DIR/hot-wallet-monitor.log" 2>&1 &
      sleep 2
      log "P0 monitor started pid $(pgrep -f autonomous_monitor.py | head -1 || echo none)"
    fi
  else
    log "P0 monitor readiness: FAIL"; FAIL=$((FAIL + 1))
  fi

  # ── P1: Hot wallet intel (read-only) ─────────────────────────
  log ""
  log "▶ P1: hot-wallet-ops + dossier + payroll verdict"
  export TARGET_WALLET
  $ORCH run hot-wallet-ops --quiet >> "$LOG_DIR/goal-hot-wallet-ops.log" 2>&1 || { log "WARN hot-wallet-ops"; FAIL=$((FAIL + 1)); }
  python3 "$ROOT/scripts/forensics/hot_wallet_dossier.py" >> "$LOG_DIR/goal-dossier.log" 2>&1 || true
  python3 "$ROOT/scripts/forensics/incident_postmortem.py" >> "$LOG_DIR/goal-postmortem.log" 2>&1 || true
  bash "$ROOT/scripts/run-payroll-otc-close.sh" >> "$LOG_DIR/goal-payroll.log" 2>&1 || true
  log "P1 artifacts: artifacts/forensics/hot-wallet-dossier.md incident-total-compromise.json"

  # ── P1: Attack surface (Jenkins — documented path, не IDOR/SQLi) ─
  log ""
  log "▶ P1: infra + Jenkins CVE + web pentest (defensive)"
  $ORCH run defensive-disclosure --quiet >> "$LOG_DIR/goal-disclosure.log" 2>&1 || true
  bash "$ROOT/scripts/run-web-app-pentest.sh" "$JENKINS" >> "$LOG_DIR/goal-web-pentest.log" 2>&1 || true
  $ORCH dispatch Agent-Vuln-05 passive-cve-check --quiet >> "$LOG_DIR/goal-cve.log" 2>&1 || true
  $ORCH dispatch Agent-Web-04 stealth-recon --quiet >> "$LOG_DIR/goal-web04.log" 2>&1 || true

  # ── P2: IR trigger check ─────────────────────────────────────
  log ""
  log "▶ P2: IR trigger status"
  if grep -q HOT_WALLET_OUTFLOW "$ROOT/artifacts/alerts.log" 2>/dev/null; then
    log "⚠️  HOT_WALLET_OUTFLOW present — run IR per docs/forensics/INCIDENT-CONCLUSION.md"
    FAIL=$((FAIL + 1))
  else
    log "IR trigger: none (expected — no unauthorized outflow)"
  fi
  grep -i heartbeat "$LOG_DIR/hot-wallet-monitor.log" 2>/dev/null | tail -1 | tee -a "$GOAL_LOG" || \
    grep -i heartbeat "$ROOT/artifacts/monitor/autonomous_state.json" 2>/dev/null | tail -1 | tee -a "$GOAL_LOG" || true

  # ── Summary ──────────────────────────────────────────────────
  log ""
  log "▶ Master report"
  $ORCH dispatch Agent-Report-06 generate-vps-master-report --quiet >> "$LOG_DIR/goal-master.log" 2>&1 || true

  cat > "$ROOT/artifacts/goal-run/SUMMARY.md" <<EOF
# Goal Run — $(date -u +%Y-%m-%dT%H:%M:%SZ)

**Mission:** Preventive IR for \`$TARGET_WALLET\`

## Done
- [x] hexstrike-server :8888
- [x] autonomous_monitor + combat readiness
- [x] hot-wallet-ops + dossier
- [x] Jenkins defensive-disclosure + web pentest
- [x] payroll/incident artifacts

## NOT run (out of scope / closed)
- Full 7 forensics re-run (case CLOSED)
- sandbox-battle / field-targets fork (no Anvil on VPS)
- Unauthorized transfer / rescue (not triggered)

## Verify daily
\`\`\`bash
grep heartbeat /var/log/hexstrike/hot-wallet-monitor.log | tail -1
grep HOT_WALLET_OUTFLOW artifacts/alerts.log || echo OK
curl -s http://127.0.0.1:8888/health | head -c 200
\`\`\`

**fail_count:** $FAIL
EOF

  log "══════════════════════════════════════════════════════"
  log " GOAL RUN COMPLETE — fail_count=$FAIL"
  log " Summary: artifacts/goal-run/SUMMARY.md"
  log " Log:     $GOAL_LOG"
  log "══════════════════════════════════════════════════════"
  return $FAIL
}

if [[ "$BACKGROUND" -eq 1 ]]; then
  : > "$GOAL_LOG"
  nohup bash -c "$(declare -f run_goal); run_goal" >> "$GOAL_LOG" 2>&1 &
  echo "PID $! — tail -f $GOAL_LOG"
else
  run_goal
fi
