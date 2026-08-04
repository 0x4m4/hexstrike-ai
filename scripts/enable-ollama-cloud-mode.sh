#!/usr/bin/env bash
# enable-ollama-cloud-mode.sh — Ollama Cloud via local offload or ollama.com direct API
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-local-cloud}"
LOCAL_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
CLOUD_HOST="${OLLAMA_CLOUD_HOST:-https://ollama.com}"
LOCAL_CLOUD_MODEL="${OLLAMA_CLOUD_MODEL:-qwen3-coder:480b-cloud}"
DIRECT_MODEL="${OLLAMA_CLOUD_DIRECT_MODEL:-qwen3.5:397b}"
ENV_FILE="$ROOT/.env"

touch "$ENV_FILE"
set_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

echo "=== HexStrike Ollama Cloud Mode (${MODE}) ==="

if [[ "$MODE" == "direct" ]]; then
  if [[ -z "${OLLAMA_API_KEY:-}" ]]; then
    echo "[FAIL] OLLAMA_API_KEY is required for direct cloud API"
    echo "       Create a key at https://ollama.com/settings/keys"
    exit 1
  fi
  set_env "LLM_PROVIDER" "ollama-cloud"
  set_env "OLLAMA_HOST" "$CLOUD_HOST"
  set_env "LLM_BASE_URL" "${CLOUD_HOST%/}/v1"
  set_env "LLM_MODEL" "$DIRECT_MODEL"
  set_env "OLLAMA_MODEL" "$DIRECT_MODEL"
  set_env "CURSOR_INTEGRATION_MODE" "CLOUD_PRIMARY"
  export LLM_PROVIDER=ollama-cloud
  export OLLAMA_HOST="$CLOUD_HOST"
  export LLM_BASE_URL="${CLOUD_HOST%/}/v1"
  export LLM_MODEL="$DIRECT_MODEL"
  export OLLAMA_MODEL="$DIRECT_MODEL"
  echo "[OK]   Direct cloud API → ${CLOUD_HOST} (model=${DIRECT_MODEL})"
else
  if ! curl -sf --max-time 3 "${LOCAL_HOST}/api/tags" >/dev/null 2>&1; then
    echo "[FAIL] Local Ollama not reachable at ${LOCAL_HOST} — start: ollama serve"
    exit 1
  fi
  echo "[INFO] Ensure you are signed in: ollama signin"
  echo "[INFO] Pull cloud model: ollama pull ${LOCAL_CLOUD_MODEL}"
  set_env "LLM_PROVIDER" "ollama-local-cloud"
  set_env "OLLAMA_HOST" "$LOCAL_HOST"
  set_env "LLM_BASE_URL" "${LOCAL_HOST%/}/v1"
  set_env "LLM_MODEL" "$LOCAL_CLOUD_MODEL"
  set_env "OLLAMA_MODEL" "$LOCAL_CLOUD_MODEL"
  set_env "OLLAMA_BYPASS_TUNNEL" "true"
  set_env "CURSOR_INTEGRATION_MODE" "OFFLINE_PRIMARY"
  export LLM_PROVIDER=ollama-local-cloud
  export OLLAMA_HOST="$LOCAL_HOST"
  export LLM_BASE_URL="${LOCAL_HOST%/}/v1"
  export LLM_MODEL="$LOCAL_CLOUD_MODEL"
  export OLLAMA_MODEL="$LOCAL_CLOUD_MODEL"
  echo "[OK]   Local cloud offload → ${LOCAL_HOST} (model=${LOCAL_CLOUD_MODEL})"
fi

echo ""
python3 - <<'PY'
import json, sys
sys.path.insert(0, "src")
from hexstrike.llm.provider import LocalLlmProvider

p = LocalLlmProvider()
print(json.dumps({"status": p.status(), "latency": p.measure_hook_latency(probe="models")}, indent=2))
PY
