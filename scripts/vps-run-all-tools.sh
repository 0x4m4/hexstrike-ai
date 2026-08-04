#!/usr/bin/env bash
# VPS: запуск всех HexStrike инструментов и workflow
# Usage on Server:
#   cd /opt/hexstrike-ai && bash scripts/vps-run-all-tools.sh
#   bash scripts/vps-run-all-tools.sh --skip-forensics   # быстрее (~5 min)
#   bash scripts/vps-run-all-tools.sh --background       # nohup в фоне
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# VPS env
if [[ -f "$ROOT/scripts/forensics-env-vps.sh" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/scripts/forensics-env-vps.sh"
fi

export TARGET="${TARGET:-http://51.250.97.223:8080}"
export JENKINS_TARGET="${JENKINS_TARGET:-http://51.250.97.223:8080}"
export HEXSTRIKE_URL="${HEXSTRIKE_URL:-http://127.0.0.1:8888}"

log() { echo "[vps-run-all] $*"; }
warn() { echo "[vps-run-all] WARN: $*"; }

# Pull latest
if git rev-parse --git-dir >/dev/null 2>&1; then
  log "git pull origin master"
  git fetch origin master 2>/dev/null || true
  git pull origin master 2>/dev/null || warn "git pull skipped"
fi

# Activate venv if present
if [[ -f "$ROOT/hexstrike_env/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/hexstrike_env/bin/activate"
fi

# systemd services (VPS production)
if command -v systemctl >/dev/null 2>&1; then
  log "Restart hexstrike services"
  systemctl restart hexstrike-server 2>/dev/null || true
  systemctl restart hexstrike-orchestrator 2>/dev/null || true
  sleep 2
  systemctl is-active hexstrike-server hexstrike-orchestrator 2>/dev/null || true
fi

# Ensure monitor running (single instance)
if ! pgrep -f 'autonomous_monitor.py' >/dev/null 2>&1; then
  log "Start autonomous_monitor"
  mkdir -p /var/log/hexstrike
  nohup python3 -u scripts/autonomous_monitor.py >> /var/log/hexstrike/hot-wallet-monitor.log 2>&1 &
fi

BACKGROUND=0
EXTRA=()
for arg in "$@"; do
  case "$arg" in
    --background) BACKGROUND=1 ;;
    *) EXTRA+=("$arg") ;;
  esac
done

RUN="$ROOT/scripts/run-all-tools.sh ${EXTRA[*]:-}"

if [[ "$BACKGROUND" -eq 1 ]]; then
  LOG="/var/log/hexstrike/run-all-tools.log"
  mkdir -p /var/log/hexstrike
  log "Background: $LOG"
  nohup bash -c "$RUN" >> "$LOG" 2>&1 &
  echo "PID $! — tail -f $LOG"
else
  log "Foreground run"
  bash "$ROOT/scripts/run-all-tools.sh" "${EXTRA[@]}"
fi
