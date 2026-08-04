#!/usr/bin/env bash
# bootstrap-ollama-autopilot.sh — zero-touch Ollama + Cursor models setup
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ARTIFACT="$ROOT/artifacts/ollama-setup-status.json"
MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
LOG="/tmp/hexstrike-ollama-autopilot.log"

mkdir -p "$ROOT/artifacts" "$(dirname "$LOG")"
: > "$LOG"

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

write_status() {
  PYTHONPATH=src python3 - "$ARTIFACT" "$LOG" <<'PY'
import json, sys
from pathlib import Path
from datetime import datetime, timezone

from hexstrike.llm.provider import LocalLlmProvider, resolve_llm_config

artifact = Path(sys.argv[1])
log_path = Path(sys.argv[2])
cfg = resolve_llm_config()
provider = LocalLlmProvider(cfg)
data = provider.status()
data["latency_models"] = provider.measure_hook_latency(probe="models")
data["latency_chat"] = provider.measure_hook_latency(probe="chat")
data["timestamp"] = datetime.now(timezone.utc).isoformat()
if log_path.exists():
    data["autopilot_log_tail"] = log_path.read_text(encoding="utf-8")[-4000:]
artifact.parent.mkdir(parents=True, exist_ok=True)
artifact.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"[OK] status -> {artifact}")
PY
}

install_ollama_linux() {
  if command -v ollama >/dev/null 2>&1; then
    log "ollama CLI already installed"
    return 0
  fi
  log "Installing Ollama (Linux)..."
  if ! command -v zstd >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y -qq zstd
  fi
  curl -fsSL https://ollama.com/install.sh | sh >>"$LOG" 2>&1
}

ensure_ollama_serve() {
  if curl -sf --max-time 3 "${HOST}/api/tags" >/dev/null 2>&1; then
    log "Ollama API already up at ${HOST}"
    return 0
  fi
  log "Starting ollama serve (cpu_avx2, background)..."
  if command -v tmux >/dev/null 2>&1 && [[ -f /exec-daemon/tmux.portal.conf ]]; then
    tmux -f /exec-daemon/tmux.portal.conf kill-session -t ollama-serve 2>/dev/null || true
    tmux -f /exec-daemon/tmux.portal.conf new-session -d -s ollama-serve -c "$ROOT" -- \
      "${SHELL:-bash}" -lc "OLLAMA_LLM_LIBRARY=\${OLLAMA_LLM_LIBRARY:-cpu_avx2} OLLAMA_NUM_PARALLEL=1 ollama serve >>$LOG 2>&1"
  else
    nohup env OLLAMA_LLM_LIBRARY="${OLLAMA_LLM_LIBRARY:-cpu_avx2}" OLLAMA_NUM_PARALLEL=1 \
      ollama serve >>"$LOG" 2>&1 &
  fi
  for _ in $(seq 1 30); do
    curl -sf --max-time 2 "${HOST}/api/tags" >/dev/null 2>&1 && { log "Ollama ready"; return 0; }
    sleep 1
  done
  log "WARN: Ollama API not ready after 30s"
  return 1
}

pull_model() {
  if ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
    log "Model family present: ${MODEL}"
    return 0
  fi
  log "Pulling ${MODEL}..."
  ollama pull "$MODEL" >>"$LOG" 2>&1
}

log "=== HexStrike Ollama Autopilot ==="
log "Model: ${MODEL} | Host: ${HOST}"

if [[ "$(uname -s)" == "Linux" ]]; then
  install_ollama_linux
elif [[ "$(uname -s)" == "Darwin" ]]; then
  if ! command -v ollama >/dev/null 2>&1; then
    log "Install Ollama.app from https://ollama.com/download or: brew install ollama"
    exit 1
  fi
fi

ensure_ollama_serve || true
pull_model || true

log "Writing Cursor model registry + .env ..."
export OLLAMA_MODEL="$MODEL"
"$ROOT/scripts/enable-system-integration-mode.sh" >>"$LOG" 2>&1 || true

log "Orchestrator handshake ..."
python3 "$ROOT/hexstrike_orchestrator.py" llm-handshake >>"$LOG" 2>&1 || true

write_status
log "=== Autopilot complete — see ${ARTIFACT} ==="
