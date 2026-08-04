#!/usr/bin/env bash
# Три целевых прогона по CURSOR-RULES / TARGETS / DAILY / operator-audit
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=/dev/null
if [[ -d /opt/drainer-intel ]] || [[ "${HEXSTRIKE_VPS:-}" == "1" ]]; then
  source "$ROOT/scripts/forensics-env-vps.sh"
else
  source "$ROOT/scripts/forensics-env-mac.sh"
fi

export PATH="${HOME}/.foundry/bin:${PATH}"
mkdir -p "$ROOT/artifacts/recon" "$ROOT/artifacts/intel" "$ROOT/artifacts/forensics"
cp -f "$ROOT/docs/recon/"* "$ROOT/artifacts/recon/" 2>/dev/null || true
cp -a "$ROOT/docs/intel/." "$ROOT/artifacts/intel/" 2>/dev/null || true
[[ -d "$ROOT/docs/recon/vanilla-drainer-intel" ]] && \
  cp -a "$ROOT/docs/recon/vanilla-drainer-intel/." "$ROOT/artifacts/recon/vanilla-drainer-intel/" 2>/dev/null || true

failed=0
save_run() {
  local tag="$1" wf="$2"
  local latest="$ROOT/artifacts/orchestrator/latest.json"
  [[ -f "$latest" ]] && cp "$latest" "$ROOT/artifacts/orchestrator/latest-${tag}.json"
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  HexStrike — 3 прогона (режим forensics)                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "Репозитории:"
echo "  TRX:    ${TRX_DRAINER_REPO}"
echo "  EVM:    ${EVM_DRAINER_REPO}"
echo "  Ape:    ${APETERMINAL_REPO}"
echo "  Solana: ${SOLANA_DRAINER_REPO}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ПРОГОН 1/3: operator-lab"
echo " Цели: operator-audit.txt, CURSOR-RULES.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if python3 scripts/hexstrike-orchestrator.py run operator-lab --quiet; then
  save_run "operator-lab" "operator-lab"
  echo "[OK] Прогон 1 завершён"
else
  echo "[FAIL] Прогон 1"
  failed=$((failed + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ПРОГОН 2/3: field-targets-5"
echo " Цели: TARGETS-REPORT-20260707.md (5 кошельков BSC)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if python3 scripts/hexstrike-orchestrator.py run field-targets-5 --quiet; then
  save_run "field-targets" "field-targets-5"
  echo "[OK] Прогон 2 завершён"
else
  echo "[FAIL] Прогон 2"
  failed=$((failed + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ПРОГОН 3/3: run-all-forensics"
echo " Цели: DAILY-REPORT-20260707.md + 7 malware/contract модулей"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$ROOT/scripts/run-all-forensics.sh"; then
  echo "{\"failed\": 0, \"modules\": 7, \"success\": true}" > "$ROOT/artifacts/forensics/session-summary.json"
  echo "[OK] Прогон 3 завершён"
else
  echo "{\"failed\": 1, \"modules\": 7, \"success\": false}" > "$ROOT/artifacts/forensics/session-summary.json"
  echo "[FAIL] Прогон 3"
  failed=$((failed + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Сводный отчёт (RU)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
export PROGON_FAILED_COUNT="$failed"
python3 scripts/forensics/generate_session_report.py || true

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
printf "║  ИТОГ: %s из 3 прогонов                                  ║\n" "$((3 - failed))/3"
echo "╚══════════════════════════════════════════════════════════╝"
exit $(( failed > 0 ? 1 : 0 ))
