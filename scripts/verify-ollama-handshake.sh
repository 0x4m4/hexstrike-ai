#!/usr/bin/env bash
# verify-ollama-handshake.sh — diagnostic for Cursor ↔ Ollama integration
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Load project .env when present
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

export OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_ORIGINS="${OLLAMA_ORIGINS:-*}"
INTEGRATION_MODE="${CURSOR_INTEGRATION_MODE:-}"
OFFLINE_PRIMARY=0
[[ "$INTEGRATION_MODE" == "OFFLINE_PRIMARY" ]] && OFFLINE_PRIMARY=1
[[ "${OLLAMA_BYPASS_TUNNEL:-}" == "true" ]] && OFFLINE_PRIMARY=1

if [[ -f "$ROOT/.cursor/settings.json" ]] && python3 -c "
import json,sys
d=json.load(open('$ROOT/.cursor/settings.json'))
sys.exit(0 if d.get('systemIntegrationMode')=='OFFLINE_PRIMARY' or d.get('cursor',{}).get('routing',{}).get('offlinePrimary') else 1)
" 2>/dev/null; then
  OFFLINE_PRIMARY=1
fi

echo "=== HexStrike Ollama Handshake Diagnostic ==="
echo "Time: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "OLLAMA_HOST: $OLLAMA_HOST"
echo "OLLAMA_ORIGINS: $OLLAMA_ORIGINS"
echo "CURSOR_INTEGRATION_MODE: ${INTEGRATION_MODE:-unset}"
echo "OFFLINE_PRIMARY: $([[ $OFFLINE_PRIMARY -eq 1 ]] && echo yes || echo no)"
echo ""

FAIL=0

check() {
  local name="$1"
  local ok="$2"
  local detail="$3"
  if [[ "$ok" == "1" ]]; then
    echo "[OK]   $name — $detail"
  else
    echo "[FAIL] $name — $detail"
    FAIL=$((FAIL + 1))
  fi
}

measure_ms() {
  local url="$1"
  local method="${2:-GET}"
  local data="${3:-}"
  if [[ "$method" == "POST" && -n "$data" ]]; then
    curl -sf --max-time 120 -o /dev/null -w "%{time_total}" \
      -X POST "$url" -H "Content-Type: application/json" -d "$data" 2>/dev/null || echo "nan"
  else
    curl -sf --max-time 10 -o /dev/null -w "%{time_total}" "$url" 2>/dev/null || echo "nan"
  fi
}

# 1. TCP socket
HOST_PORT="${OLLAMA_HOST#http://}"
HOST_PORT="${HOST_PORT#https://}"
HOST="${HOST_PORT%%:*}"
PORT="${HOST_PORT##*:}"
[[ "$PORT" == "$HOST" ]] && PORT=11434

if timeout 3 bash -c "echo >/dev/tcp/$HOST/$PORT" 2>/dev/null; then
  check "tcp_socket" 1 "$HOST:$PORT reachable"
else
  check "tcp_socket" 0 "$HOST:$PORT connection refused or timeout — is 'ollama serve' running?"
fi

# 2. GET /api/tags
TAGS_RESP="$(curl -sf --max-time 5 "${OLLAMA_HOST}/api/tags" 2>&1)" && TAGS_OK=1 || TAGS_OK=0
if [[ "$TAGS_OK" == "1" ]]; then
  check "api_tags" 1 "GET /api/tags OK"
  if echo "$TAGS_RESP" | grep -qi "qwen2.5-coder"; then
    check "model_qwen_coder" 1 "qwen2.5-coder present in model list"
  else
    check "model_qwen_coder" 0 "qwen2.5-coder NOT found — run: ollama pull qwen2.5-coder:7b"
    echo "       Available models:"
    echo "$TAGS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('       ', [m.get('name') for m in d.get('models',[])])" 2>/dev/null || true
  fi
else
  check "api_tags" 0 "GET /api/tags failed: $TAGS_RESP"
fi

# 3. OpenAI-compatible /v1/models
MODELS_RESP="$(curl -sf --max-time 5 "${OLLAMA_HOST}/v1/models" 2>&1)" && MODELS_OK=1 || MODELS_OK=0
if [[ "$MODELS_OK" == "1" ]]; then
  check "openai_v1_models" 1 "GET /v1/models OK (Cursor uses this schema)"
else
  check "openai_v1_models" 0 "GET /v1/models failed: $MODELS_RESP"
fi

# 4. Minimal chat completion (chain-of-thought probe)
CHAT_MODEL="${OLLAMA_MODEL:-${LLM_MODEL:-qwen2.5-coder:7b}}"
# Prefer installed tag when full model name absent
if [[ "$TAGS_OK" == "1" ]] && ! echo "$TAGS_RESP" | grep -q "\"name\":\"${CHAT_MODEL}\""; then
  CHAT_MODEL="$(echo "$TAGS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); names=[m.get('name','') for m in d.get('models',[])]; print(next((n for n in names if 'qwen2.5-coder' in n), names[0] if names else 'qwen2.5-coder:7b'))" 2>/dev/null || echo "qwen2.5-coder:7b")"
fi

AUTH_HEADER=()
if [[ -n "${OLLAMA_API_KEY:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${OLLAMA_API_KEY}")
fi

CHAT_RESP="$(curl -sf --max-time 120 "${OLLAMA_HOST}/v1/chat/completions" \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${CHAT_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: pong\"}],\"stream\":false,\"options\":{\"num_thread\":${OLLAMA_NUM_THREAD:-16},\"num_predict\":${OLLAMA_NUM_PREDICT:-512},\"num_ctx\":${OLLAMA_NUM_CTX:-32768}}}" 2>&1)" && CHAT_OK=1 || CHAT_OK=0
if [[ "$CHAT_OK" == "1" ]]; then
  check "chat_completion" 1 "POST /v1/chat/completions OK (model=${CHAT_MODEL})"
  if echo "$CHAT_RESP" | grep -qi "think\|pong"; then
    check "reasoning_path" 1 "model responded (CoT/reasoning capable)"
  fi
else
  check "chat_completion" 0 "POST /v1/chat/completions failed: ${CHAT_RESP:0:200}"
fi

# 5. Public tunnel — skipped in OFFLINE_PRIMARY / localhost bypass
PUBLIC_URL="${OLLAMA_PUBLIC_BASE_URL:-}"
LOCAL_PUBLIC=0
[[ "$PUBLIC_URL" == *"127.0.0.1"* || "$PUBLIC_URL" == *"localhost"* ]] && LOCAL_PUBLIC=1

if [[ $OFFLINE_PRIMARY -eq 1 ]]; then
  check "tunnel_bypass" 1 "OFFLINE_PRIMARY — Cloud VM tunnel bypassed; routing to ${OLLAMA_HOST}/v1"
elif [[ -n "$PUBLIC_URL" ]]; then
  TUNNEL_MODELS="$(curl -sf --max-time 10 "${PUBLIC_URL%/}/models" 2>&1)" && TUN_OK=1 || TUN_OK=0
  if [[ "$TUN_OK" == "1" ]]; then
    check "tunnel_v1_models" 1 "GET ${PUBLIC_URL}/models OK (Cursor Override URL)"
  else
    check "tunnel_v1_models" 0 "Tunnel failed: $TUNNEL_MODELS"
  fi
fi

# 6. Cursor localhost note (only when not OFFLINE_PRIMARY desktop)
if [[ $OFFLINE_PRIMARY -eq 0 && ( -z "$PUBLIC_URL" || $LOCAL_PUBLIC -eq 1 ) ]]; then
  echo ""
  echo "[WARN] Cursor cloud backend cannot reach localhost directly."
  echo "       Run ./scripts/enable-system-integration-mode.sh on your Mac for OFFLINE_PRIMARY,"
  echo "       or start cloudflared and set OLLAMA_PUBLIC_BASE_URL to the tunnel /v1 URL."
fi

# 7. settings.json + integration mode lock
if [[ -f "$ROOT/.cursor/settings.json" ]]; then
  check "cursor_settings" 1 ".cursor/settings.json present"
  if python3 -c "
import json
d=json.load(open('$ROOT/.cursor/settings.json'))
assert d.get('systemIntegrationMode')=='OFFLINE_PRIMARY'
assert d['cursor']['openai']['baseUrl'].startswith('http://127.0.0.1')
" 2>/dev/null; then
    check "offline_primary_lock" 1 "OFFLINE_PRIMARY locked — localhost base URL enforced"
  else
    check "offline_primary_lock" 0 "Run ./scripts/enable-system-integration-mode.sh to lock OFFLINE_PRIMARY"
  fi
else
  check "cursor_settings" 0 ".cursor/settings.json missing"
fi

# 8. Latency self-diagnostic
MODELS_MS="$(measure_ms "${OLLAMA_HOST}/v1/models")"
CHAT_MS="$(measure_ms "${OLLAMA_HOST}/v1/chat/completions" POST "{\"model\":\"${CHAT_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"stream\":false,\"options\":{\"num_thread\":${OLLAMA_NUM_THREAD:-16},\"num_predict\":${OLLAMA_NUM_PREDICT:-512},\"num_ctx\":${OLLAMA_NUM_CTX:-32768}}}")"
echo ""
echo "=== Latency (model-to-hook round-trip) ==="
if [[ "$MODELS_MS" != "nan" ]]; then
  MODELS_MS_FMT="$(python3 -c "print(f'{float('$MODELS_MS')*1000:.2f}')" 2>/dev/null || echo "$MODELS_MS")"
  echo "GET  /v1/models           : ${MODELS_MS_FMT} ms"
else
  echo "GET  /v1/models           : unreachable"
fi
if [[ "$CHAT_MS" != "nan" ]] && python3 -c "float('$CHAT_MS')" 2>/dev/null; then
  CHAT_MS_FMT="$(python3 -c "print(f'{float('$CHAT_MS')*1000:.2f}')" 2>/dev/null || echo "$CHAT_MS")"
  echo "POST /v1/chat/completions : ${CHAT_MS_FMT} ms (model=${CHAT_MODEL})"
else
  echo "POST /v1/chat/completions : unreachable or inference error (model=${CHAT_MODEL})"
fi

echo ""
echo "=== Summary: failures=$FAIL ==="
exit "$FAIL"
