#!/usr/bin/env bash
# setup-sim800c.sh — detect SIM800C, install deps, run AT diagnostic
# Run ON THE MACHINE where USB-UART + SIM800C are physically connected (Mac/Linux).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="${HEXSTRIKE_VENV:-$ROOT/hexstrike-env}"
LOG_PREFIX="[sim800c]"

log()  { echo "$LOG_PREFIX $*"; }
warn() { echo "$LOG_PREFIX WARN: $*" >&2; }
die()  { echo "$LOG_PREFIX ERROR: $*" >&2; exit 1; }

log "=== SIM800C setup ==="
log "Root: $ROOT"

# ── 1. OS packages ─────────────────────────────────────────────
if command -v apt-get >/dev/null 2>&1; then
  log "Installing serial tools (apt)..."
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    minicom screen picocom usbutils 2>/dev/null || warn "apt install partial"
elif command -v brew >/dev/null 2>&1; then
  log "macOS: ensure CH340/CP2102 driver + minicom if needed"
  brew list minicom >/dev/null 2>&1 || brew install minicom 2>/dev/null || true
fi

# ── 2. Python pyserial ─────────────────────────────────────────
if [[ -f "$VENV/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install -q pyserial
else
  python3 -m pip install --user pyserial 2>/dev/null || \
    python3 -m pip install --break-system-packages pyserial 2>/dev/null || \
    die "Cannot install pyserial"
fi

# ── 3. Permissions (Linux) ─────────────────────────────────────
if [[ "$(uname -s)" == "Linux" ]] && getent group dialout >/dev/null 2>&1; then
  if ! groups | grep -q dialout; then
    warn "User not in dialout group. Run: sudo usermod -aG dialout \$USER && re-login"
  fi
fi

# ── 4. USB scan ────────────────────────────────────────────────
log "USB devices:"
if command -v lsusb >/dev/null 2>&1; then
  lsusb | grep -iE '1a86|10c4|0403|serial|uart|ch340|cp210|ftdi' || lsusb
else
  system_profiler SPUSBDataType 2>/dev/null | grep -A3 -iE 'serial|ch340|cp210|ftdi' || true
fi

log "Serial ports:"
ls /dev/ttyUSB* /dev/ttyACM* /dev/cu.usb* /dev/cu.SLAB* /dev/cu.wch* 2>/dev/null || \
  echo "  (none found — check cable, power 4V, TX/RX)"

# ── 5. AT diagnostic ───────────────────────────────────────────
log "Running AT diagnostic..."
PORT="${SIM800C_PORT:-}"
BAUD="${SIM800C_BAUD:-}"
ARGS=()
[[ -n "$PORT" ]] && ARGS+=(--port "$PORT")
[[ -n "$BAUD" ]] && ARGS+=(--baud "$BAUD")

if python3 "$ROOT/scripts/gsm/sim800c_diagnose.py" "${ARGS[@]}"; then
  log "SIM800C OK — module responds to AT commands"
  log "Manual test: minicom -D \$(jq -r .modem.port artifacts/gsm/sim800c-diagnose.json) -b \$(jq -r .modem.baud artifacts/gsm/sim800c-diagnose.json)"
  exit 0
fi

cat <<'EOF'

[FAIL] SIM800C not detected. Checklist:
  1. Power: 4.0V, up to 2A peak, common GND with USB-TTL
  2. Wiring: SIM800C TXD → USB RXD, RXD → USB TXD (3.3V logic!)
  3. Antenna connected, SIM inserted (no PIN or AT+CPIN="1234")
  4. Baud: try SIM800C_BAUD=115200 or 9600
  5. Linux: sudo usermod -aG dialout $USER && re-login
  6. Operator 2G: many carriers disable GSM — try another SIM

EOF
exit 1
