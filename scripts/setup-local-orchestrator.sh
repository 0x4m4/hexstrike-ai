#!/usr/bin/env bash
# setup-local-orchestrator.sh — один раз: Ollama + HexStrike terminal (без Cursor)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="${HEXSTRIKE_OLLAMA_MODEL:-hexstrike-orchestrator}"
HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

echo "=== HexStrike Local Orchestrator Setup ==="

if ! command -v ollama &>/dev/null; then
  echo "[FAIL] Установи Ollama: brew install ollama"
  exit 1
fi

if ! curl -sf --max-time 5 "${HOST}/api/tags" >/dev/null; then
  echo "[FAIL] Ollama не запущен. Открой Ollama.app или: ollama serve"
  exit 1
fi

if ! ollama list 2>/dev/null | grep -q 'deepseek-r1:7b'; then
  echo "[pull] deepseek-r1:7b (средняя модель) ..."
  ollama pull deepseek-r1:7b
fi

if [[ -f "$ROOT/config/hexstrike-orchestrator.modelfile" ]]; then
  echo "[create] модель ${MODEL} ..."
  ollama create "${MODEL}" -f "$ROOT/config/hexstrike-orchestrator.modelfile" 2>/dev/null || \
    ollama create "${MODEL}" -f "$ROOT/config/hexstrike-orchestrator.modelfile"
fi

chmod +x "$ROOT/scripts/hexstrike-terminal.py"
chmod +x "$ROOT/hexstrike-orchestrator" 2>/dev/null || true

# .env
touch "$ROOT/.env"
for kv in \
  "OLLAMA_HOST=${HOST}" \
  "OLLAMA_ORIGINS=*" \
  "LLM_PROVIDER=ollama-local" \
  "LLM_MODEL=deepseek-r1:7b" \
  "HEXSTRIKE_OLLAMA_MODEL=${MODEL}" \
  "CURSOR_INTEGRATION_MODE=OFFLINE_PRIMARY"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$ROOT/.env" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${kv}|" "$ROOT/.env"
  else
    echo "${kv}" >> "$ROOT/.env"
  fi
done

echo ""
echo "[OK] Готово."
echo ""
echo "Запуск терминального оркестратора:"
echo "  cd $ROOT && python3 scripts/hexstrike-terminal.py"
echo ""
echo "Или сразу workflow без чата:"
echo "  ./hexstrike-orchestrator run defensive-disclosure"
echo "  ./hexstrike-orchestrator run vps-full-readonly"
echo ""
echo "Внутри терминала:"
echo "  /help"
echo "  /run defensive-disclosure"
echo "  /dispatch Agent-Vuln-05 passive-cve-check"
