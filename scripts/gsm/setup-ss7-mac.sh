#!/usr/bin/env bash
# setup-ss7-mac.sh — SS7 на Mac через Linux VM/Docker (Osmocom не работает нативно на macOS)
#
# SIM800C остаётся на Mac (UART).
# SS7-стек (Osmocom STP/HLR/MSC) — на Linux (VPS или Docker).
#
# Usage:
#   bash scripts/gsm/setup-ss7-mac.sh              # инструкции + проверка SIM800C
#   bash scripts/gsm/setup-ss7-mac.sh --vps      # деплой SS7 на VPS
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VPS_HOST="${VPS_HOST:-78.27.235.70}"
VPS_USER="${VPS_USER:-root}"
LOG_PREFIX="[ss7-mac]"

log()  { echo "$LOG_PREFIX $*"; }
warn() { echo "$LOG_PREFIX WARN: $*" >&2; }

[[ "$(uname -s)" == "Darwin" ]] || { log "Не macOS — используйте: bash scripts/gsm/setup-ss7-lab.sh"; exit 0; }

deploy_vps() {
  log "Деплой SS7 lab на VPS ${VPS_USER}@${VPS_HOST}..."
  if [[ -n "${VPS_SSH_KEY:-}" && -f "$VPS_SSH_KEY" ]]; then
    SSH=(ssh -i "$VPS_SSH_KEY" -o StrictHostKeyChecking=accept-new)
  else
    SSH=(ssh -o StrictHostKeyChecking=accept-new)
  fi
  "${SSH[@]}" "${VPS_USER}@${VPS_HOST}" bash -s <<'REMOTE'
set -euo pipefail
INSTALL="${HEXSTRIKE_ROOT:-/opt/hexstrike-ai}"
if [[ ! -d "$INSTALL" ]]; then
  INSTALL="/opt/hexstrike-ai"
  git clone --depth 1 https://github.com/banda198565/hexstrike-ai.git "$INSTALL" 2>/dev/null || true
fi
cd "$INSTALL"
git fetch origin cursor/ss7-sim800c-setup-2512 2>/dev/null && git checkout cursor/ss7-sim800c-setup-2512 2>/dev/null || true
bash scripts/gsm/setup-ss7-lab.sh
REMOTE
  log "SS7 lab на VPS готов. Проверка:"
  "${SSH[@]}" "${VPS_USER}@${VPS_HOST}" "cat /opt/hexstrike-ai/artifacts/gsm/ss7-lab-status.json 2>/dev/null || echo 'status pending'"
}

log "=== SS7 + SIM800C на Mac ==="

cat <<'ARCH'

Архитектура на Mac:

  ┌─────────────┐   UART/USB    ┌──────────────┐
  │  SIM800C    │──────────────▶│  Mac (iMac)  │  ← GSM: SMS, регистрация
  │  GSM модем  │   /dev/cu.*   │  AT-команды  │
  └─────────────┘               └──────┬───────┘
                                       │ SSH (опционально)
                                       ▼
                               ┌──────────────┐
                               │  Linux VPS   │  ← SS7: OsmoSTP/HLR/MSC
                               │  SCTP :2905  │
                               └──────────────┘

ВАЖНО: SIM800C ≠ SS7. Модуль не подключается к SS7 напрямую.

ARCH

log "Шаг 1: SIM800C на Mac..."
if bash "$ROOT/scripts/gsm/setup-sim800c-mac.sh"; then
  log "SIM800C: OK"
else
  warn "SIM800C: не найден — подключите USB-UART и повторите"
fi

if [[ "${1:-}" == "--vps" ]]; then
  deploy_vps
else
  cat <<'NEXT'

SS7 на Mac нативно не поддерживается (нужен SCTP/Linux).

Варианты:
  A) VPS (рекомендуется):
     VPS_HOST=78.27.235.70 bash scripts/gsm/setup-ss7-mac.sh --vps

  B) Docker на Mac:
     docker run -it --privileged ubuntu:24.04 bash
     apt update && apt install -y osmo-stp osmo-hlr osmo-msc

  C) Только GSM (без SS7):
     SIM800C на Mac достаточен для SMS/USSD/GPRS через AT-команды.

NEXT
fi
