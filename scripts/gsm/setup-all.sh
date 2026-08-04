#!/usr/bin/env bash
# setup-all.sh — one-shot: SS7 lab + SIM800C diagnostic
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== HexStrike GSM/SS7 setup ==="
echo "Step 1/2: SS7 lab (Osmocom)..."
bash "$ROOT/scripts/gsm/setup-ss7-lab.sh" || echo "[WARN] SS7 lab partial — needs Linux + SCTP"

echo ""
echo "Step 2/2: SIM800C diagnostic..."
bash "$ROOT/scripts/gsm/setup-sim800c.sh" || echo "[WARN] SIM800C not found on this host"

echo ""
echo "Reports:"
ls -la "$ROOT/artifacts/gsm/" 2>/dev/null || true
