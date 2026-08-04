#!/usr/bin/env bash
# Run operator + field-target tests from CURSOR-RULES / TARGETS / DAILY reports
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p "$ROOT/artifacts/recon"
cp -f "$ROOT/docs/recon/"* "$ROOT/artifacts/recon/" 2>/dev/null || true

echo "=== HexStrike operator targets test ==="
echo "Inputs:"
echo "  docs/recon/CURSOR-RULES.txt"
echo "  docs/recon/operator-audit.txt"
echo "  docs/recon/TARGETS-REPORT-20260707.md"
echo "  docs/recon/DAILY-REPORT-20260707.md"
echo "────────────────────────────────────────"

failed=0

echo "[1/2] operator-lab"
if ! python3 scripts/hexstrike-orchestrator.py run operator-lab --quiet; then
  failed=$((failed + 1))
fi

echo "[2/2] field-targets-5"
if ! python3 scripts/hexstrike-orchestrator.py run field-targets-5 --quiet; then
  failed=$((failed + 1))
fi

echo "=== Operator targets test complete (failed=${failed}) ==="
exit $(( failed > 0 ? 1 : 0 ))
