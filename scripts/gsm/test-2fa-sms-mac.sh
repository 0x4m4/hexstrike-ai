#!/usr/bin/env bash
# test-2fa-sms-mac.sh — тест приёма SMS 2FA через SIM800C (СВОЙ номер)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${SIM800C_PORT:-/dev/cu.usbserial-1420}"
BAUD="${SIM800C_BAUD:-115200}"
DURATION="${SMS_MONITOR_SEC:-180}"

[[ "$(uname -s)" == "Darwin" ]] || { echo "Запускайте на Mac"; exit 2; }

if [[ -f "$ROOT/hexstrike-env/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/hexstrike-env/bin/activate"
fi

echo "=== 2FA SMS test (authorized — your SIM only) ==="
echo "Port: $PORT | Baud: $BAUD | Listen: ${DURATION}s"
echo ""
echo "Сейчас запросите код 2FA на ЛЮБОМ СВОЁМ тестовом аккаунте."
echo "Код появится здесь автоматически."
echo ""

python3 "$ROOT/scripts/gsm/sms_monitor.py" \
  --port "$PORT" \
  --baud "$BAUD" \
  --duration "$DURATION"
