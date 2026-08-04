#!/bin/bash
# HexStrike Master Initialization Script (Local Autonomy Mode)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEXSTRIKE_ROOT="${HEXSTRIKE_ROOT:-$SCRIPT_DIR}"
VENV_ACTIVATE="$HEXSTRIKE_ROOT/hexstrike-env/bin/activate"
PYTHON_BIN="$HEXSTRIKE_ROOT/hexstrike-env/bin/python3"
LOG_FILE="$HEXSTRIKE_ROOT/hexstrike.log"
PORT="${HEXSTRIKE_PORT:-8888}"
MODEL="${OLLAMA_MODEL:-deepseek-r1:1.5b}"

fail() {
  echo "[FAIL] $1"
  exit 1
}

warn() {
  echo "[WARN] $1"
}

step() {
  echo "[STEP] $1"
}

step "[1/4] Инициализация окружения..."
cd "$HEXSTRIKE_ROOT"

if [[ ! -f "$VENV_ACTIVATE" ]]; then
  fail "venv не найден: $VENV_ACTIVATE"
fi

# shellcheck disable=SC1090
source "$VENV_ACTIVATE"

if [[ ! -x "$PYTHON_BIN" ]]; then
  fail "Python в venv не найден: $PYTHON_BIN"
fi

mkdir -p "$HEXSTRIKE_ROOT/data/rag" "$HEXSTRIKE_ROOT/scripts" "$HEXSTRIKE_ROOT/src"
: > "$LOG_FILE"

step "[2/4] Проверка Ollama и локальной модели..."
if command -v ollama >/dev/null 2>&1; then
  if ! ollama list | grep -q "$MODEL"; then
    echo "Загрузка модели $MODEL..."
    ollama pull "$MODEL"
  else
    echo "Модель $MODEL уже доступна"
  fi
else
  warn "Ollama не установлена. Продолжаем в OFFLINE_PRIMARY без LLM handshake."
fi

step "[3/4] Проверка API и Handshake..."
if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo "HexStrike API уже запущен на порту ${PORT}"
else
  step "[4/4] Запуск RAG-контура и оркестратора..."
  nohup "$PYTHON_BIN" "$HEXSTRIKE_ROOT/src/hexstrike_orchestrator.py" \
    --mode=OFFLINE_PRIMARY \
    --port "$PORT" \
    >> "$LOG_FILE" 2>&1 &
  ORCH_PID=$!
  echo "Orchestrator PID: $ORCH_PID"

  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

"$PYTHON_BIN" "$HEXSTRIKE_ROOT/scripts/verify-ollama-handshake.py" | tee -a "$LOG_FILE"

if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo "--- HexStrike готов к работе ---"
  echo "API доступен на http://localhost:${PORT}"
  echo "Логи: $LOG_FILE"
else
  fail "HexStrike API не поднялся на порту ${PORT}. Смотри $LOG_FILE"
fi
