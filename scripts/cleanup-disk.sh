#!/usr/bin/env bash
# cleanup-disk.sh — освободить место: Ollama модели + мусор HexStrike
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== ДО очистки ==="
df -h / /Volumes/Eva 2>/dev/null | head -5 || df -h . | head -3
echo ""
du -sh ~/.ollama 2>/dev/null || echo "ollama: нет"
du -sh "${ROOT}/artifacts" 2>/dev/null || true

KEEP="${HEXSTRIKE_KEEP_MODEL:-deepseek-v2.5}"

echo ""
echo "=== Удаляю лишние Ollama-модели (оставляю ${KEEP}) ==="
if command -v ollama >/dev/null; then
  ollama list 2>/dev/null | awk 'NR>1 {print $1}' | while read -r m; do
    case "$m" in
      "${KEEP}"|"${KEEP}"*) echo "  keep  $m" ;;
      *) echo "  rm    $m"; ollama rm "$m" 2>/dev/null || true ;;
    esac
  done
else
  echo "  ollama не установлен"
fi

echo ""
echo "=== Чищу артефакты оркестратора (логи прогонов) ==="
rm -rf "${ROOT}/artifacts/orchestrator/"*.json 2>/dev/null || true
mkdir -p "${ROOT}/artifacts/orchestrator"
echo "  ok"

echo ""
echo "=== Чищу Python/кэш ==="
find "${ROOT}" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "${ROOT}" -name '*.pyc' -delete 2>/dev/null || true
pip cache purge 2>/dev/null || true
conda clean -a -y 2>/dev/null || true
rm -rf /tmp/hexstrike-* /tmp/hexstrike-fast.modelfile 2>/dev/null || true

echo ""
echo "=== Опционально: старые артефакты recon (освободит много) ==="
echo "  Чтобы удалить ВСЕ artifacts кроме jenkins-cve-report:"
echo "  rm -rf ${ROOT}/artifacts/2026-* ${ROOT}/artifacts/orchestrator ${ROOT}/artifacts/orchestrator"

echo ""
echo "=== ПОСЛЕ ==="
df -h / /Volumes/Eva 2>/dev/null | head -5 || df -h . | head -3
du -sh ~/.ollama 2>/dev/null || true
ollama list 2>/dev/null || true
echo "[OK] готово. Запуск: ./hexstrike-go.sh"
