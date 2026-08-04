#!/usr/bin/env bash
# mac-start-ollama.sh — start Ollama on Mac + qwen2.5-coder + Cursor config
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

log() { echo "[mac-ollama] $*"; }

[[ "$(uname -s)" == "Darwin" ]] || { log "Run this ON YOUR MAC (not cloud agent)"; exit 1; }

if ! command -v ollama >/dev/null 2>&1; then
  log "Installing via Homebrew..."
  brew install ollama
fi

log "Starting Ollama.app..."
open -a Ollama 2>/dev/null || true
open -a "Ollama" 2>/dev/null || true

log "Waiting for API at ${HOST}..."
for i in $(seq 1 45); do
  curl -sf --max-time 2 "${HOST}/api/tags" >/dev/null 2>&1 && break
  sleep 1
  [[ "$i" -eq 45 ]] && {
    log "Ollama not up — trying: ollama serve"
    nohup ollama serve >/tmp/ollama-serve-mac.log 2>&1 &
    sleep 3
  }
done

curl -sf --max-time 5 "${HOST}/api/tags" >/dev/null \
  || { log "FAIL — open Ollama.app manually from Applications"; exit 1; }

if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
  log "Pulling ${MODEL}..."
  ollama pull "$MODEL"
fi

export OLLAMA_MODEL="$MODEL"
"$ROOT/scripts/enable-system-integration-mode.sh"

log "Done. Cursor: http://127.0.0.1:11434/v1 | API Key: ollama | Model: ${MODEL}"
ollama list
