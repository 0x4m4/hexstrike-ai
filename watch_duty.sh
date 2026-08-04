#!/usr/bin/env bash
# watch_duty.sh — supervise HexStrike services 24/7 with auto-restart
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

ARTIFACTS_DIR="$ROOT/artifacts"
DUTY_LOG="$ARTIFACTS_DIR/duty.log"
PID_DIR="$ARTIFACTS_DIR/pids"
mkdir -p "$ARTIFACTS_DIR" "$PID_DIR"

log() {
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*" | tee -a "$DUTY_LOG"
}

# Load API key from .env
if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "$ROOT/.env" | grep -E '^(HEXSTRIKE_API_KEY|GITHUB_WEBHOOK_SECRET)=' | xargs) 2>/dev/null || true
fi

if [[ -z "${HEXSTRIKE_API_KEY:-}" ]]; then
  log "[!] HEXSTRIKE_API_KEY not set. Copy .env.example to .env and configure a key."
  exit 1
fi

# Prefer project venv when available
if [[ -x "$ROOT/hexstrike-env/bin/python3" ]]; then
  PYTHON="$ROOT/hexstrike-env/bin/python3"
elif [[ -x "$ROOT/hexstrike_env/bin/python3" ]]; then
  PYTHON="$ROOT/hexstrike_env/bin/python3"
else
  PYTHON="python3"
fi

ORCHESTRATOR="$ROOT/hexstrike_orchestrator.py"
SERVER="$ROOT/hexstrike_server.py"
HEALTH="$ROOT/scripts/health_check.sh"
MONITOR_LEGACY="$ROOT/scripts/autonomous_monitor.py"
HEALTH_INTERVAL="${HEXSTRIKE_HEALTH_INTERVAL_SEC:-300}"

is_running() {
  local pidfile="$1"
  [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null
}

start_server() {
  local pidfile="$PID_DIR/hexstrike_server.pid"
  if is_running "$pidfile"; then
    log "API server already running (pid $(cat "$pidfile"))"
    return 0
  fi
  log "Starting hexstrike_server.py..."
  nohup "$PYTHON" "$SERVER" >>"$ARTIFACTS_DIR/server.log" 2>&1 &
  echo $! >"$pidfile"
  log "API server started pid=$(cat "$pidfile")"
}

stop_server() {
  local pidfile="$PID_DIR/hexstrike_server.pid"
  if is_running "$pidfile"; then
    kill "$(cat "$pidfile")" 2>/dev/null || true
    rm -f "$pidfile"
  fi
}

run_health() {
  if [[ -x "$HEALTH" ]]; then
    log "Running health_check.sh..."
    "$HEALTH" 2>&1 | tee -a "$DUTY_LOG" || log "health_check reported failures (see above)"
  fi
  if [[ -f "$ORCHESTRATOR" ]]; then
    "$PYTHON" "$ORCHESTRATOR" manifest 2>&1 | tee -a "$DUTY_LOG" || true
  fi
}

cleanup() {
  log "Shutting down supervised services..."
  stop_server
  exit 0
}
trap cleanup SIGINT SIGTERM

log "Боевое дежурство HexStrike-AI начато."
log "Python: $PYTHON"
log "Orchestrator: $ORCHESTRATOR"
log "Stealth: ${HEXSTRIKE_STEALTH:-1} | Health interval: ${HEALTH_INTERVAL}s"

run_health
start_server

last_health=0

while true; do
  now=$(date +%s)
  if (( now - last_health >= HEALTH_INTERVAL )); then
    run_health
    last_health=$now
  fi

  if ! is_running "$PID_DIR/hexstrike_server.pid"; then
    log "API server down — restarting..."
    start_server
  fi

  log "Запуск orchestrator monitor..."
  if [[ -f "$ORCHESTRATOR" ]]; then
    "$PYTHON" "$ORCHESTRATOR" monitor 2>&1 | tee -a "$DUTY_LOG" || true
  elif [[ -f "$MONITOR_LEGACY" ]]; then
    "$PYTHON" "$MONITOR_LEGACY" 2>&1 | tee -a "$DUTY_LOG" || true
  else
    log "[!] No monitor entrypoint found"
    sleep 10
    continue
  fi

  log "Monitor loop exited — перезапуск через 5 секунд..."
  sleep 5
done
