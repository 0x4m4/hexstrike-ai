#!/usr/bin/env bash
# enable-system-integration-mode.sh — localhost-first Cursor ↔ Ollama integration
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOCAL_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
LOCAL_BASE="${LOCAL_HOST%/}/v1"
MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
SETTINGS="$ROOT/.cursor/settings.json"
ENV_FILE="$ROOT/.env"

echo "=== HexStrike System Integration Mode ==="
echo "Detecting local Ollama at $LOCAL_HOST ..."

if ! curl -sf --max-time 3 "${LOCAL_HOST}/api/tags" >/dev/null 2>&1; then
  echo "[FAIL] Ollama not reachable at $LOCAL_HOST — start: ollama serve"
  exit 1
fi

TAGS="$(curl -sf --max-time 5 "${LOCAL_HOST}/api/tags")"
if ! echo "$TAGS" | grep -qi 'qwen2.5-coder'; then
  echo "[WARN] qwen2.5-coder not in manifest — run: ollama pull qwen2.5-coder:7b"
  echo "       Available: $(echo "$TAGS" | python3 -c "import sys,json; d=json.load(sys.stdin); print([m.get('name') for m in d.get('models',[])])" 2>/dev/null || echo '?')"
else
  echo "[OK]   qwen2.5-coder present in local model manifest"
fi

touch "$ENV_FILE"
set_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

set_env "OLLAMA_HOST" "$LOCAL_HOST"
set_env "OLLAMA_ORIGINS" "*"
set_env "OLLAMA_PUBLIC_BASE_URL" "$LOCAL_BASE"
set_env "OLLAMA_BYPASS_TUNNEL" "true"
set_env "LLM_PROVIDER" "ollama-local"
set_env "LLM_BASE_URL" "$LOCAL_BASE"
set_env "LLM_MODEL" "$MODEL"
set_env "CURSOR_INTEGRATION_MODE" "OFFLINE_PRIMARY"

export OLLAMA_HOST="$LOCAL_HOST"
export OLLAMA_PUBLIC_BASE_URL="$LOCAL_BASE"
export OLLAMA_BYPASS_TUNNEL=true
export LLM_PROVIDER=ollama-local
export LLM_BASE_URL="$LOCAL_BASE"
export LLM_MODEL="$MODEL"
export CURSOR_INTEGRATION_MODE=OFFLINE_PRIMARY

mkdir -p "$(dirname "$SETTINGS")"
python3 - "$SETTINGS" "$LOCAL_BASE" "$MODEL" <<'PY'
import json, sys
from pathlib import Path

settings_path = Path(sys.argv[1])
base_url = sys.argv[2]
model = sys.argv[3]

OLLAMA_MODELS = [
    ("qwen2.5-coder:7b", "Qwen2.5 Coder 7B (Ollama)", {"num_thread": 16, "num_predict": 512, "num_ctx": 32768}),
    ("qwen2.5-coder:14b", "Qwen2.5 Coder 14B (Ollama)", {"num_thread": 16, "num_predict": 512, "num_ctx": 32768}),
    ("qwen2.5-coder:32b", "Qwen2.5 Coder 32B (Ollama)", {"num_thread": 16, "num_predict": 512, "num_ctx": 32768}),
    ("qwen3-coder:480b-cloud", "Qwen3 Coder 480B Cloud (Ollama)", None),
]

custom = []
for mid, label, opts in OLLAMA_MODELS:
    entry = {
        "id": mid,
        "name": label,
        "provider": "openai-compatible",
        "model_type": "openai_compatible",
        "baseUrl": base_url,
        "apiKey": "ollama",
        "supportsChainOfThought": False,
    }
    if opts:
        entry["options"] = opts
    if mid.endswith("-cloud"):
        entry["cloud"] = True
    custom.append(entry)

settings = {
    "$schema": "https://cursor.com/schemas/settings.json",
    "_comment": "Ollama + Qwen2.5-Coder — localhost OpenAI-compatible models",
    "systemIntegrationMode": "OFFLINE_PRIMARY",
    "AUTHORIZED_OPERATOR_MODE": False,
    "ollama": {
        "host": "http://127.0.0.1:11434",
        "model": model,
        "openai_compatible_base": base_url,
        "api_key_placeholder": "ollama",
        "pull_commands": [
            "ollama pull qwen2.5-coder:7b",
            "ollama pull qwen2.5-coder:14b",
        ],
        "options": {"num_thread": 16, "num_predict": 512, "num_ctx": 32768},
    },
    "cursor": {
        "chat": {
            "defaultModel": model,
            "useLocalLlm": True,
            "model_type": "openai_compatible",
        },
        "composer": {
            "defaultModel": model,
            "useLocalLlm": True,
            "model_type": "openai_compatible",
        },
        "maxMode": {
            "defaultModel": "qwen2.5-coder:14b",
            "preferHighReasoning": True,
            "routeToLocal": True,
            "model_type": "openai_compatible",
        },
        "models": {"custom": custom, "disabled": []},
        "openai": {
            "overrideBaseUrl": True,
            "baseUrl": base_url,
            "apiKey": "ollama",
            "model_type": "openai_compatible",
        },
        "routing": {
            "preferLocalhost": True,
            "bypassTunnel": True,
            "offlinePrimary": True,
            "tunnelFallback": False,
        },
    },
    "env": {
        "OLLAMA_HOST": "http://127.0.0.1:11434",
        "OLLAMA_ORIGINS": "*",
        "OLLAMA_PUBLIC_BASE_URL": base_url,
        "OLLAMA_BYPASS_TUNNEL": "true",
        "LLM_PROVIDER": "ollama-local",
        "LLM_BASE_URL": base_url,
        "LLM_MODEL": model,
        "OLLAMA_NUM_THREAD": "16",
        "OLLAMA_NUM_PREDICT": "512",
        "OLLAMA_NUM_CTX": "32768",
        "CURSOR_INTEGRATION_MODE": "OFFLINE_PRIMARY",
    },
}

settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
print(f"[OK]   Wrote {settings_path} ({len(custom)} Ollama models registered)")
PY

echo "[OK]   .env updated — localhost bypasses Cloud VM tunnel"
echo ""
echo "Running handshake verification ..."
"$ROOT/scripts/verify-ollama-handshake.sh"
VERIFY_RC=$?

echo ""
echo "Measuring model-to-Cursor hook latency ..."
python3 - <<'PY'
import json, sys
sys.path.insert(0, "src")
from hexstrike.llm.provider import LocalLlmProvider

p = LocalLlmProvider()
models_lat = p.measure_hook_latency(probe="models")
chat_lat = p.measure_hook_latency(probe="chat")
print(json.dumps({"models_probe": models_lat, "chat_probe": chat_lat}, indent=2))
PY

exit "$VERIFY_RC"
