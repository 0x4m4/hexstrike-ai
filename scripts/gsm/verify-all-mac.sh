#!/usr/bin/env bash
# verify-all-mac.sh — полная проверка USB + SIM800C на Mac
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT="$ROOT/artifacts/gsm/verify-all-report.json"
PORT="${SIM800C_PORT:-/dev/cu.usbserial-1420}"
BAUD="${SIM800C_BAUD:-115200}"
LOG_PREFIX="[verify-all]"

log()  { echo "$LOG_PREFIX $*"; }
ok()   { echo "$LOG_PREFIX OK: $*"; }
fail() { echo "$LOG_PREFIX FAIL: $*" >&2; }

[[ "$(uname -s)" == "Darwin" ]] || { fail "Только macOS"; exit 2; }

mkdir -p "$ROOT/artifacts/gsm"
PASS=0
FAIL=0

check() {
  local name=$1 result=$2
  if [[ "$result" == "pass" ]]; then
    ok "$name"
    PASS=$((PASS + 1))
  else
    fail "$name — $result"
    FAIL=$((FAIL + 1))
  fi
}

log "=== Полная проверка GSM/SIM800C ==="
log "Host: $(scutil --get ComputerName 2>/dev/null || hostname)"
log "macOS: $(sw_vers -productVersion 2>/dev/null)"
echo ""

# 1. USB port
log "--- 1/4 USB ---"
if [[ -e "$PORT" ]]; then
  check "USB port $PORT exists" "pass"
  ls -la "$PORT"
else
  CU=$(ls /dev/cu.usb* /dev/cu.usbserial* 2>/dev/null | grep -v Bluetooth | head -1 || true)
  if [[ -n "$CU" ]]; then
    PORT="$CU"
    check "USB port auto-detected: $PORT" "pass"
  else
    check "USB port" "not found"
  fi
fi
echo ""

# 2. pyserial
log "--- 2/4 pyserial ---"
if [[ -f "$ROOT/hexstrike-env/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/hexstrike-env/bin/activate"
fi
if python3 - <<PY
from serial.tools import list_ports
for p in list_ports.comports():
    if "bluetooth" not in (p.description or "").lower():
        print(f"  {p.device} vid={p.vid} pid={p.pid}")
PY
then
  check "pyserial" "pass"
else
  check "pyserial" "import failed"
fi
echo ""

# 3. AT diagnostic
log "--- 3/4 SIM800C AT ---"
if python3 "$ROOT/scripts/gsm/sim800c_diagnose.py" \
    --port "$PORT" --baud "$BAUD" \
    --json-out "$ROOT/artifacts/gsm/sim800c-diagnose.json"; then
  check "SIM800C AT @ $BAUD" "pass"
else
  log "Retry baud 9600..."
  if python3 "$ROOT/scripts/gsm/sim800c_diagnose.py" \
      --port "$PORT" --baud 9600 \
      --json-out "$ROOT/artifacts/gsm/sim800c-diagnose.json"; then
    BAUD=9600
    check "SIM800C AT @ 9600" "pass"
  else
    check "SIM800C AT" "no response"
  fi
fi
echo ""

# 4. Summary JSON
log "--- 4/4 Report ---"
python3 - <<PY
import json
from pathlib import Path

diag_path = Path("$ROOT/artifacts/gsm/sim800c-diagnose.json")
diag = json.loads(diag_path.read_text()) if diag_path.exists() else {}
modem = diag.get("modem") or {}
cmds = modem.get("commands") or {}

report = {
    "timestamp": diag.get("timestamp"),
    "port": modem.get("port", "$PORT"),
    "baud": modem.get("baud", "$BAUD"),
    "usb_ok": bool(modem.get("port")),
    "at_ok": modem.get("at_ok", False),
    "sim_ready": "READY" in cmds.get("sim_pin", ""),
    "registered": ",1" in cmds.get("network_reg", "") or ",5" in cmds.get("network_reg", ""),
    "signal": cmds.get("signal", "").strip(),
    "operator": cmds.get("operator", "").strip(),
    "imei": cmds.get("imei", "").strip(),
    "checks_passed": $PASS,
    "checks_failed": $FAIL,
    "verdict": "OK" if modem.get("at_ok") and "READY" in cmds.get("sim_pin", "") else "FAIL",
}
out = Path("$REPORT")
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(report, indent=2, ensure_ascii=False))
PY

echo ""
if [[ "$FAIL" -eq 0 ]] && grep -q '"verdict": "OK"' "$REPORT" 2>/dev/null; then
  ok "ВСЁ РАБОТАЕТ — USB + SIM800C + сеть"
  echo ""
  echo "Настройки:"
  echo "  SIM800C_PORT=$PORT"
  echo "  SIM800C_BAUD=$BAUD"
  exit 0
else
  fail "Есть проблемы — см. $REPORT"
  exit 1
fi
