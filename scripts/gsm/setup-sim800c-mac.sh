#!/usr/bin/env bash
# setup-sim800c-mac.sh — SIM800C на macOS (iMac/MacBook)
# Запускать НА МАКЕ, где физически подключён USB-UART + SIM800C.
#
# Usage:
#   cd /Volumes/Eva/mufasaai-storage/hexstrike-ai   # или ваш путь
#   bash scripts/gsm/setup-sim800c-mac.sh
#
#   # если порт известен:
#   SIM800C_PORT=/dev/cu.usbserial-1410 bash scripts/gsm/setup-sim800c-mac.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="${HEXSTRIKE_VENV:-$ROOT/hexstrike-env}"
LOG_PREFIX="[sim800c-mac]"

log()  { echo "$LOG_PREFIX $*"; }
warn() { echo "$LOG_PREFIX WARN: $*" >&2; }
die()  { echo "$LOG_PREFIX ERROR: $*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "Этот скрипт только для macOS. На Linux: bash scripts/gsm/setup-sim800c.sh"

log "=== SIM800C setup (macOS) ==="
log "Root: $ROOT"

# ── 1. Homebrew tools ──────────────────────────────────────────
if ! command -v brew >/dev/null 2>&1; then
  die "Homebrew не найден. Установите: https://brew.sh"
fi

log "Проверка Homebrew-пакетов..."
for pkg in minicom python@3.12; do
  if ! brew list "$pkg" >/dev/null 2>&1; then
    log "Устанавливаю $pkg..."
    brew install "$pkg"
  fi
done

# ── 2. USB-UART драйверы (CH340 / CP2102) ─────────────────────
log "USB-устройства:"
system_profiler SPUSBDataType 2>/dev/null | \
  grep -B1 -A5 -iE 'CH340|CP210|FTDI|USB Serial|UART|wch.cn|Silicon Labs' || \
  warn "USB-UART адаптер не найден в system_profiler"

USB_CU_PORTS=$(ls /dev/cu.usb* /dev/cu.SLAB* /dev/cu.wch* /dev/cu.usbserial* /dev/cu.usbmodem* 2>/dev/null || true)
if [[ -z "$USB_CU_PORTS" ]]; then
  warn "Serial-порты USB не найдены."
  log "Запуск глубокой USB-диагностики..."
  bash "$ROOT/scripts/gsm/mac-usb-deep-scan.sh" || true
  cat <<'DRV'

Если /dev/cu.* пустой — проблема НЕ в SIM800C, а в USB/драйвере:
  1. Замените USB-кабель (многие только для зарядки!)
  2. Подключите адаптер в другой порт iMac
  3. Установите драйвер:
     CH340:  https://github.com/WCHSoftGroup/ch34xser_mac
     CP2102: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
  4. System Settings → Privacy & Security → Allow (драйвер)
  5. Тест: подключите ТОЛЬКО USB-UART без SIM800C → ls /dev/cu.*

DRV
else
  echo "$USB_CU_PORTS"
fi

# ── 3. Python + pyserial ───────────────────────────────────────
if [[ -f "$VENV/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
else
  python3 -m venv "$VENV"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
fi
pip install -q pyserial

# ── 4. Показать порты (на Mac используйте /dev/cu.*, не /dev/tty.*) ──
log "Доступные serial-порты (используйте cu.*):"
CU_LIST=$(ls /dev/cu.* 2>/dev/null | grep -vE 'Bluetooth|debug-console|JBL|Bose|AirPods' || true)
if [[ -z "$CU_LIST" ]]; then
  warn "Нет ни одного /dev/cu.* (кроме Bluetooth) — USB-UART не определяется macOS"
else
  echo "$CU_LIST"
fi

# ── 5. AT-диагностика ──────────────────────────────────────────
log "Запуск AT-диагностики..."
PORT="${SIM800C_PORT:-}"
BAUD="${SIM800C_BAUD:-}"
ARGS=()
[[ -n "$PORT" ]] && ARGS+=(--port "$PORT")
[[ -n "$BAUD" ]] && ARGS+=(--baud "$BAUD")

REPORT="$ROOT/artifacts/gsm/sim800c-diagnose.json"
mkdir -p "$ROOT/artifacts/gsm"

if python3 "$ROOT/scripts/gsm/sim800c_diagnose.py" --json-out "$REPORT" "${ARGS[@]}"; then
  DETECTED_PORT="$(python3 -c "import json; print(json.load(open('$REPORT'))['modem']['port'])")"
  DETECTED_BAUD="$(python3 -c "import json; print(json.load(open('$REPORT'))['modem']['baud'])")"
  log "SIM800C OK: $DETECTED_PORT @ $DETECTED_BAUD"
  cat <<EOF

Ручная проверка:
  minicom -D $DETECTED_PORT -b $DETECTED_BAUD

В minicom наберите:
  AT
  AT+CPIN?
  AT+CSQ
  AT+CREG?

Выход из minicom: Ctrl-A, затем X

EOF
  exit 0
fi

cat <<'EOF'

[FAIL] SIM800C не отвечает на AT. Чеклист для Mac:

  1. Питание: 4.0V отдельный БП (до 2A), GND общий с USB-UART
  2. Провода: TXD модуля → RXD адаптера, RXD → TXD (3.3V!)
  3. Порт: на Mac только /dev/cu.* (не /dev/tty.*)
  4. Baud: SIM800C_BAUD=115200 или 9600
  5. SIM: без PIN, антенна подключена
  6. 2G: многие операторы отключили GSM — попробуйте другую SIM

Пример с явным портом:
  SIM800C_PORT=/dev/cu.usbserial-1410 SIM800C_BAUD=115200 bash scripts/gsm/setup-sim800c-mac.sh

EOF
exit 1
