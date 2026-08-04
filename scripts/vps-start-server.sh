#!/usr/bin/env bash
# VPS: установка и запуск hexstrike_server (:8888) + monitor + проверка
#
# На Server (root):
#   cd /opt/hexstrike-ai
#   git pull origin master
#   bash scripts/vps-start-server.sh
#
# Опции:
#   --install-only   только systemd + venv, без restart
#   --no-monitor     не трогать autonomous_monitor
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
INSTALL_DIR="$ROOT"
PORT="${HEXSTRIKE_PORT:-8888}"
LOG_DIR="/var/log/hexstrike"

INSTALL_ONLY=0
NO_MONITOR=0
for arg in "$@"; do
  case "$arg" in
    --install-only) INSTALL_ONLY=1 ;;
    --no-monitor) NO_MONITOR=1 ;;
  esac
done

log()  { echo "[vps-server] $*"; }
ok()   { echo "[vps-server] OK: $*"; }
warn() { echo "[vps-server] WARN: $*"; }
die()  { echo "[vps-server] ERROR: $*" >&2; exit 1; }

[[ $(id -u) -eq 0 ]] || die "Запускайте как root на VPS: ssh root@78.27.235.70"

mkdir -p "$LOG_DIR" "$ROOT/artifacts/run-all-tools"

# ── 1. Git pull ────────────────────────────────────────────────
if [[ -d "$ROOT/.git" ]]; then
  log "git pull origin master"
  git config --global --add safe.directory "$ROOT" 2>/dev/null || true
  git fetch origin master 2>/dev/null || true
  git pull origin master 2>/dev/null || warn "git pull failed — продолжаем с текущей версией"
  log "HEAD: $(git log -1 --oneline 2>/dev/null || echo unknown)"
fi

# ── 2. Python venv + deps ──────────────────────────────────────
if [[ ! -f "$ROOT/hexstrike_env/bin/python3" ]]; then
  log "Creating venv hexstrike_env"
  python3 -m venv "$ROOT/hexstrike_env"
fi
# shellcheck source=/dev/null
source "$ROOT/hexstrike_env/bin/activate"

log "Installing Python deps (flask, requests, psutil)..."
pip install -q --upgrade pip
pip install -q 'flask>=2.3,<4' 'requests>=2.31' 'psutil>=5.9'

# ── 3. VPS env ─────────────────────────────────────────────────
if [[ -f "$ROOT/scripts/forensics-env-vps.sh" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/scripts/forensics-env-vps.sh"
fi
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
fi

# ── 4. systemd: hexstrike-server ───────────────────────────────
log "Installing systemd unit: hexstrike-server"
cat >/etc/systemd/system/hexstrike-server.service <<UNIT
[Unit]
Description=HexStrike AI Tools API Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment=HEXSTRIKE_PORT=$PORT
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/hexstrike_env/bin/python3 $INSTALL_DIR/hexstrike_server.py --port $PORT
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/hexstrike-server.log
StandardError=append:$LOG_DIR/hexstrike-server.log

[Install]
WantedBy=multi-user.target
UNIT

# orchestrator watch (если ещё нет)
if [[ ! -f /etc/systemd/system/hexstrike-orchestrator.service ]]; then
  log "Installing systemd unit: hexstrike-orchestrator"
  cat >/etc/systemd/system/hexstrike-orchestrator.service <<UNIT
[Unit]
Description=HexStrike orchestrator watch queue
After=network-online.target hexstrike-server.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/hexstrike_env/bin/python3 $INSTALL_DIR/scripts/hexstrike-orchestrator.py watch
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT
fi

systemctl daemon-reload
systemctl enable hexstrike-server hexstrike-orchestrator 2>/dev/null || true

[[ "$INSTALL_ONLY" -eq 1 ]] && { ok "install-only complete"; exit 0; }

# ── 5. Start services ──────────────────────────────────────────
log "Starting hexstrike-server + hexstrike-orchestrator"
systemctl restart hexstrike-server
systemctl restart hexstrike-orchestrator
sleep 3

# ── 6. Health check ────────────────────────────────────────────
HEALTH_URL="http://127.0.0.1:${PORT}/health"
if curl -sf --max-time 8 "$HEALTH_URL" >/tmp/hexstrike-health.json 2>/dev/null; then
  ok "hexstrike_server UP — $HEALTH_URL"
  python3 - <<'PY'
import json
d=json.load(open("/tmp/hexstrike-health.json"))
print(f"  version: {d.get('version')}")
print(f"  tools:   {d.get('total_tools_available')}/{d.get('total_tools_count')} installed")
for cat, st in d.get("category_stats", {}).items():
    if st.get("available", 0) > 0:
        print(f"  {cat}: {st['available']}/{st['total']}")
PY
else
  warn "health check failed — journalctl -u hexstrike-server -n 40"
  journalctl -u hexstrike-server -n 20 --no-pager 2>/dev/null || tail -20 "$LOG_DIR/hexstrike-server.log"
  exit 1
fi

systemctl is-active hexstrike-server hexstrike-orchestrator 2>/dev/null | while read -r s; do log "service: $s"; done

# ── 7. Monitor (hot wallet) ────────────────────────────────────
if [[ "$NO_MONITOR" -eq 0 ]]; then
  pkill -f 'autonomous_monitor.py' 2>/dev/null || true
  sleep 1
  if ! pgrep -f 'autonomous_monitor.py' >/dev/null 2>&1; then
    log "Starting autonomous_monitor (single instance)"
    nohup python3 -u "$ROOT/scripts/autonomous_monitor.py" >> "$LOG_DIR/hot-wallet-monitor.log" 2>&1 &
    sleep 2
  fi
  if pgrep -f 'autonomous_monitor.py' >/dev/null 2>&1; then
    ok "autonomous_monitor running (pid $(pgrep -f autonomous_monitor.py | head -1))"
  else
    warn "monitor failed to start"
  fi
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo " HexStrike VPS — сервер запущен"
echo "════════════════════════════════════════════════════════"
echo " API:          http://127.0.0.1:${PORT}/health"
echo " Server log:   $LOG_DIR/hexstrike-server.log"
echo " Monitor log:  $LOG_DIR/hot-wallet-monitor.log"
echo ""
echo " Команды:"
echo "   systemctl status hexstrike-server"
echo "   journalctl -u hexstrike-server -f"
echo "   curl -s http://127.0.0.1:${PORT}/health | python3 -m json.tool"
echo "   bash scripts/vps-run-all-agents.sh --background"
echo "   bash scripts/vps-run-all-tools.sh --skip-forensics"
echo "════════════════════════════════════════════════════════"
