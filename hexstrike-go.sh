#!/usr/bin/env bash
# hexstrike-go.sh — Mac-safe (no colon in unquoted bash)
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ВАЖНО: без ":" в имени — bash на Mac ломается на deepseek-v2.5:7b
CHAT_MODEL="deepseek-v2.5"
WRAPPER_MODEL="hexstrike-orchestrator"
OLLAMA_HOST="http://127.0.0.1:11434"
FASTFILE="/tmp/hexstrike-fast.modelfile"

echo "=== HexStrike go ==="

command -v ollama >/dev/null || { echo "[FAIL] brew install ollama"; exit 1; }

if ! curl -sf --max-time 5 "${OLLAMA_HOST}/api/tags" >/dev/null; then
  echo "Запускаю Ollama.app..."
  open -a Ollama 2>/dev/null || true
  sleep 10
fi

if ! curl -sf --max-time 5 "${OLLAMA_HOST}/api/tags" >/dev/null; then
  echo "[FAIL] Ollama не отвечает"
  exit 1
fi

echo "[pull] ${CHAT_MODEL} ..."
ollama list 2>/dev/null | grep -q "deepseek-v2.5" || ollama pull "${CHAT_MODEL}"

cat > "${FASTFILE}" << 'MODELEOF'
FROM deepseek-v2.5
PARAMETER num_predict 128
PARAMETER num_thread 8
PARAMETER temperature 0.3
SYSTEM Ты HexStrike Orchestrator. Отвечай кратко по-русски. Команды: /run defensive-disclosure
MODELEOF

ollama create "${WRAPPER_MODEL}" -f "${FASTFILE}" 2>/dev/null || ollama create "${WRAPPER_MODEL}" -f "${FASTFILE}"
echo "[OK] модель готова"

echo "[test] агенты..."
./hexstrike-orchestrator dispatch Agent-Vuln-05 passive-cve-check >/tmp/hs-preflight.log 2>&1 \
  && echo "[OK] artifacts/jenkins-cve-report.json" \
  || echo "[WARN] см. /tmp/hs-preflight.log"

echo ""
echo "  1) Чат + HexStrike"
echo "  2) /run defensive-disclosure (без LLM, быстро)"
echo "  3) /run vps-full-readonly"
echo "  4) ollama run"
echo "  5) Выход"
printf "Выбор [1]: "
read -r choice
[ -z "${choice}" ] && choice=1

case "${choice}" in
  1)
    export HEXSTRIKE_CHAT_MODEL="${CHAT_MODEL}"
    export OLLAMA_NUM_PREDICT=128
    export OLLAMA_NUM_THREAD=8
    exec python3 "${ROOT}/scripts/hexstrike-terminal.py"
    ;;
  2) ./hexstrike-orchestrator run defensive-disclosure ;;
  3) ./hexstrike-orchestrator run vps-full-readonly ;;
  4) exec ollama run "${WRAPPER_MODEL}" ;;
  5) exit 0 ;;
  *) exec "$0" ;;
esac
