#!/usr/bin/env bash
# setup-ss7-lab.sh — Osmocom SS7/GSM core lab (STP + HLR + MSC)
# NOTE: SIM800C is GSM modem (AT commands), NOT an SS7 endpoint.
#       This script sets up software SS7 stack for lab/research on Linux.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CFG_DIR="${SS7_CFG_DIR:-$ROOT/config/gsm}"
LOG_PREFIX="[ss7-lab]"

log()  { echo "$LOG_PREFIX $*"; }
warn() { echo "$LOG_PREFIX WARN: $*" >&2; }
die()  { echo "$LOG_PREFIX ERROR: $*" >&2; exit 1; }

[[ "$(uname -s)" == "Linux" ]] || die "SS7 lab (Osmocom) requires Linux with SCTP support"

log "=== Osmocom SS7 lab setup ==="

# ── 1. Install packages ────────────────────────────────────────
if command -v apt-get >/dev/null 2>&1; then
  log "Installing Osmocom stack..."
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    osmo-stp osmo-msc osmo-hlr osmo-bsc \
    libosmo-sigtran7t64 libsctp1 lksctp-tools \
    2>/dev/null || die "apt install failed — check Ubuntu/Debian repos"
else
  die "Only apt-based Linux supported in this script"
fi

# ── 2. SCTP check (required for M3UA/SS7 over IP) ──────────────
if ! python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP); s.close()" 2>/dev/null; then
  warn "SCTP not available in kernel — M3UA will fail until lksctp is loaded"
  warn "Try: sudo modprobe sctp && lsmod | grep sctp"
fi

# ── 3. Lab configs ─────────────────────────────────────────────
mkdir -p "$CFG_DIR"
if [[ ! -f "$CFG_DIR/osmo-stp.cfg" ]]; then
  if [[ -f /etc/osmocom/osmo-stp.cfg ]]; then
    cp /etc/osmocom/osmo-stp.cfg "$CFG_DIR/osmo-stp.cfg"
    log "Copied default osmo-stp.cfg → $CFG_DIR/"
  else
    warn "Source /etc/osmocom/osmo-stp.cfg missing — skip copy; create $CFG_DIR/osmo-stp.cfg manually"
  fi
fi

# ── 4. Start services ──────────────────────────────────────────
start_svc() {
  local name=$1
  if command -v systemctl >/dev/null 2>&1 && [[ -d /run/systemd/system ]]; then
    sudo systemctl enable --now "osmo-${name}" 2>/dev/null && \
      log "osmo-${name}: systemd started" && return 0
  fi
  warn "systemd unavailable — start manually: osmo-${name} -c /etc/osmocom/osmo-${name}.cfg"
  return 1
}

log "Starting SS7 components (order: STP → HLR → MSC)..."
start_svc stp || true
sleep 1
start_svc hlr || true
sleep 1
start_svc msc || true

# ── 5. Status ──────────────────────────────────────────────────
log "=== Status ==="
for bin in osmo-stp osmo-hlr osmo-msc; do
  if pgrep -x "$bin" >/dev/null 2>&1; then
    log "$bin: RUNNING (pid $(pgrep -x "$bin"))"
  else
    warn "$bin: not running"
  fi
done

cat <<EOF

SS7 lab stack installed.

Architecture:
  SIM800C (GSM modem)  →  AT/UART  →  SMS/voice/GPRS only
  OsmoSTP (this setup) →  M3UA/SCTP :2905  →  SS7 signaling lab

Next steps:
  1. Verify SCTP:  ss -xl | grep sctp   (or: netstat -an | grep 2905)
  2. VTY console:  telnet 127.0.0.1 4239  (osmo-stp)
  3. SIM800C test: bash scripts/gsm/setup-sim800c.sh
  4. Full cellular lab needs osmo-bsc + BTS hardware (not SIM800C)

Config dir: $CFG_DIR
Report:     artifacts/gsm/ss7-lab-status.json

EOF

mkdir -p "$ROOT/artifacts/gsm"
python3 - <<'PY' > "$ROOT/artifacts/gsm/ss7-lab-status.json"
import json, subprocess, datetime
def running(name):
    try:
        subprocess.check_output(["pgrep","-x",name], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
print(json.dumps({
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "components": {
        "osmo-stp": running("osmo-stp"),
        "osmo-hlr": running("osmo-hlr"),
        "osmo-msc": running("osmo-msc"),
    },
    "note": "SIM800C is GSM layer; SS7 is separate Osmocom stack",
}, indent=2))
PY

log "Done."
