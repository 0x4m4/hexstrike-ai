#!/usr/bin/env bash
# check-usb-mac.sh — быстрая проверка USB-UART на Mac
set -euo pipefail

echo "=== USB check (Mac) ==="
echo "Time: $(date)"
echo ""

echo "1. Serial ports (/dev/cu.*):"
CU=$(ls /dev/cu.usb* /dev/cu.SLAB* /dev/cu.wch* /dev/cu.usbserial* 2>/dev/null || true)
if [[ -n "$CU" ]]; then
  echo "$CU" | while read -r p; do echo "   OK  $p"; done
  echo ""
  echo "   USB-UART подключён и виден macOS"
else
  echo "   FAIL — USB serial порт не найден"
  echo "   → кабель / адаптер / драйвер / порт USB"
fi
echo ""

echo "2. USB devices:"
system_profiler SPUSBDataType 2>/dev/null | grep -B2 -A6 -iE 'CH340|CP210|FTDI|Serial|wch|Silicon Labs|usbserial' || \
  echo "   (USB-UART не найден в system_profiler)"
echo ""

echo "3. pyserial:"
python3 - <<'PY' 2>/dev/null || echo "   pyserial not installed"
from serial.tools import list_ports
ports = list(list_ports.comports())
if not ports:
    print("   no ports")
for p in ports:
    if "bluetooth" not in (p.description or "").lower():
        print(f"   {p.device}  vid={p.vid} pid={p.pid}  {p.description}")
PY

echo ""
if ls /dev/cu.usbserial* /dev/cu.usb* /dev/cu.wch* /dev/cu.SLAB* 2>/dev/null | grep -q .; then
  echo "ВЕРДИКТ: USB OK — адаптер виден"
  echo "Дальше: bash scripts/gsm/setup-sim800c-mac.sh"
  exit 0
else
  echo "ВЕРДИКТ: USB FAIL — адаптер не виден"
  exit 1
fi
