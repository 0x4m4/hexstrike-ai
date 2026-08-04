#!/usr/bin/env bash
# mac-usb-deep-scan.sh — глубокая диагностика USB/serial на Mac (когда /dev/cu.* пустой)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT="$ROOT/artifacts/gsm/mac-usb-scan.txt"
mkdir -p "$ROOT/artifacts/gsm"

[[ "$(uname -s)" == "Darwin" ]] || { echo "Только macOS"; exit 1; }

{
  echo "=== Mac USB/Serial Deep Scan ==="
  echo "Time: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  echo "Host: $(scutil --get ComputerName 2>/dev/null || hostname)"
  echo "macOS: $(sw_vers -productVersion 2>/dev/null)"
  echo ""

  echo "=== 1. ALL /dev/cu.* ports ==="
  ls -la /dev/cu.* 2>/dev/null || echo "(none)"
  echo ""

  echo "=== 2. ALL /dev/tty.* (USB-related) ==="
  ls -la /dev/tty.usb* /dev/tty.SLAB* /dev/tty.wch* 2>/dev/null || echo "(none)"
  echo ""

  echo "=== 3. pyserial list_ports ==="
  if [[ -f "$ROOT/hexstrike-env/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$ROOT/hexstrike-env/bin/activate"
  fi
  python3 - <<'PY' 2>/dev/null || echo "pyserial not available"
try:
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    if not ports:
        print("(no ports from pyserial)")
    for p in ports:
        print(f"  {p.device}  vid={p.vid} pid={p.pid}  {p.description}  [{p.manufacturer}]")
except Exception as e:
    print(f"error: {e}")
PY
  echo ""

  echo "=== 4. USB tree (system_profiler) ==="
  system_profiler SPUSBDataType 2>/dev/null || echo "system_profiler failed"
  echo ""

  echo "=== 5. Serial devices (ioreg) ==="
  ioreg -p IOUSB -l 2>/dev/null | grep -iE 'USB Serial|CH340|CP210|FTDI|wch|Silicon Labs|UART|modem|SIMCom' -A3 -B1 || \
    echo "(no USB-serial in ioreg)"
  echo ""

  echo "=== 6. Loaded kernel extensions (serial/usb) ==="
  kextstat 2>/dev/null | grep -iE 'ch34|cp210|ftdi|serial|wch|usb' || \
    echo "(no matching kexts — on macOS 11+ drivers are often system extensions)"
  echo ""

  echo "=== 7. System extensions (driver apps) ==="
  systemextensionsctl list 2>/dev/null | grep -iE 'ch34|wch|silicon|ftdi|serial' || \
    echo "(run: systemextensionsctl list — check if CH340/CP2102 driver is approved)"
  echo ""

  echo "=== DIAGNOSIS ==="
  USB_COUNT=$(system_profiler SPUSBDataType 2>/dev/null | grep -ciE 'CH340|CP210|FTDI|USB Serial|wch|Silicon Labs' || true)
  CU_COUNT=$(ls /dev/cu.usb* /dev/cu.SLAB* /dev/cu.wch* /dev/cu.usbserial* 2>/dev/null | wc -l | tr -d ' ')

  if [[ "$USB_COUNT" -eq 0 && "$CU_COUNT" -eq 0 ]]; then
    cat <<'DIAG'
STATUS: USB-UART адаптер НЕ ВИДЕН macOS.

Вероятные причины (по частоте):
  A) Кабель USB только для зарядки (нет линий D+/D-) — замените кабель
  B) Адаптер не подключён / мёртвый порт USB — другой порт на iMac
  C) Драйвер CH340/CP2102 не установлен или заблокирован macOS
  D) Плата SIM800C без USB — только UART-пины (нужен отдельный USB-TTL)
  E) Модуль не включён (нет питания 4V) — Mac не увидит UART без питания платы

Действия:
  1. Подключите ТОЛЬКО USB-UART адаптер (без SIM800C) — появился ли /dev/cu.* ?
  2. Если нет — проблема в кабеле/адаптере/драйвере
  3. CH340 Mac: https://github.com/WCHSoftGroup/ch34xser_mac
     После установки: System Settings → Privacy & Security → Allow driver
  4. CP2102: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
DIAG
  elif [[ "$USB_COUNT" -gt 0 && "$CU_COUNT" -eq 0 ]]; then
    cat <<'DIAG'
STATUS: USB устройство видно, но serial-порт НЕ создан → проблема ДРАЙВЕРА.
  1. Переустановите драйвер CH340/CP2102
  2. System Settings → Privacy & Security → разрешите системное расширение
  3. Перезагрузите Mac
  4. Отключите/подключите USB
DIAG
  else
    echo "STATUS: Serial-порт(ы) найдены — запустите setup-sim800c-mac.sh снова"
  fi

} | tee "$REPORT"

echo ""
echo "Report saved: $REPORT"
echo "Пришлите этот файл в чат для разбора."
