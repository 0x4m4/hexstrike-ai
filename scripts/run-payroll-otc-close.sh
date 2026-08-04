#!/usr/bin/env bash
# Payroll/OTC hypothesis verification + case closure (read-only, no withdrawal)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -d /opt/drainer-intel ]] || [[ "${HEXSTRIKE_VPS:-}" == "1" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/scripts/forensics-env-vps.sh"
else
  # shellcheck source=/dev/null
  source "$ROOT/scripts/forensics-env-mac.sh"
fi

[[ -f .env ]] && set -a && source .env && set +a

echo "[payroll-close] Step 1: exchange forensics (read-only)"
python3 scripts/exchange-forensics.py 2>/dev/null || echo "[payroll-close] WARN: exchange-forensics skipped"

echo "[payroll-close] Step 2: entity resolution"
python3 scripts/hexstrike-orchestrator.py dispatch Agent-OSINT-03 entity-resolution --quiet 2>/dev/null || \
  python3 scripts/agents/agent_osint_03_entity.py

echo "[payroll-close] Step 3: payroll/OTC verdict"
python3 scripts/forensics/payroll_otc_verdict.py

echo "[payroll-close] Step 4: refresh dossier"
python3 scripts/forensics/hot_wallet_dossier.py 2>/dev/null || true

echo ""
echo "=== CASE CLOSED ==="
echo "  artifacts/forensics/payroll-otc-verdict.md"
echo "  artifacts/forensics/payroll-otc-verdict.json"
cat artifacts/forensics/payroll-otc-verdict.md | head -25
