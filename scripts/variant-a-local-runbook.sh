#!/usr/bin/env bash
# variant-a-local-runbook.sh — Variant A: full local autonomy (iMac, no Cloud Agent)
# Run ON YOUR MAC inside hexstrike-ai repo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOCAL_HOST="http://127.0.0.1:11434"
LOCAL_BASE="${LOCAL_HOST}/v1"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  HexStrike Variant A — Local Autonomy (NO Cloud Agent)       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Step 0: must run on Mac with ollama ──────────────────────────
if ! command -v ollama &>/dev/null; then
  echo "[FAIL] ollama not found. Install: brew install ollama"
  exit 1
fi

if ! curl -sf --max-time 3 "${LOCAL_HOST}/api/tags" >/dev/null 2>&1; then
  echo "[FAIL] Ollama not running. Start: ollama serve  (or open Ollama.app)"
  exit 1
fi

echo "=== Step 2: ollama list (exact model NAME) ==="
ollama list
echo ""

MODEL="${OLLAMA_MODEL:-deepseek-r1:1.5b}"
if ! ollama list 2>/dev/null | grep -q 'deepseek-r1:1.5b'; then
  echo "[WARN] deepseek-r1:1.5b not found — pulling ..."
  ollama pull deepseek-r1:1.5b
fi
MODEL="$(ollama list 2>/dev/null | awk 'NR>1 && /deepseek-r1:1\.5b/ {print $1; exit}')"
if [[ -z "$MODEL" ]]; then
  MODEL="$(ollama list 2>/dev/null | awk 'NR>1 && /deepseek-r1/ {print $1; exit}')"
fi
if [[ -z "$MODEL" ]]; then
  echo "[FAIL] Could not resolve deepseek-r1:1.5b from ollama list"
  exit 1
fi

echo "[OK]   Exact model NAME for Cursor: ${MODEL}"
echo ""

# ── Sync .env + settings ─────────────────────────────────────────
"$ROOT/scripts/enable-system-integration-mode.sh" 2>/dev/null || true

# Force exact tag from ollama list
if grep -q '^LLM_MODEL=' "$ROOT/.env" 2>/dev/null; then
  sed -i.bak "s|^LLM_MODEL=.*|LLM_MODEL=${MODEL}|" "$ROOT/.env"
else
  echo "LLM_MODEL=${MODEL}" >> "$ROOT/.env"
fi

python3 - "$ROOT/.cursor/settings.json" "$MODEL" "$LOCAL_BASE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
model, base = sys.argv[2], sys.argv[3]
d = json.loads(p.read_text())
d["systemIntegrationMode"] = "OFFLINE_PRIMARY"
d["cursor"]["chat"]["defaultModel"] = model
d["cursor"]["composer"]["defaultModel"] = model
d["cursor"]["maxMode"]["defaultModel"] = model
d["cursor"]["models"]["custom"] = [{
    "id": model, "name": model,
    "provider": "openai-compatible",
    "model_type": "openai_compatible",
    "baseUrl": base,
    "supportsChainOfThought": True,
}]
d["cursor"]["openai"]["baseUrl"] = base
d["env"]["LLM_MODEL"] = model
p.write_text(json.dumps(d, indent=2) + "\n")
print(f"[OK]   .cursor/settings.json → model={model}")
PY

export OLLAMA_MODEL="$MODEL"
export LLM_MODEL="$MODEL"

echo ""
echo "=== Verify API (same as Cursor 'Verify' button) ==="
VERIFY_RESP="$(curl -sf --max-time 10 "${LOCAL_BASE}/models" 2>&1)" && VERIFY_OK=1 || VERIFY_OK=0
if [[ "$VERIFY_OK" == "1" ]]; then
  echo "[OK]   GET ${LOCAL_BASE}/models — green-check equivalent"
else
  echo "[FAIL] ${VERIFY_RESP}"
  exit 1
fi

CHAT_RESP="$(curl -sf --max-time 120 "${LOCAL_BASE}/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply: pong\"}],\"stream\":false,\"options\":{\"num_thread\":16,\"num_predict\":256}}" 2>&1)" && CHAT_OK=1 || CHAT_OK=0
if [[ "$CHAT_OK" == "1" ]]; then
  echo "[OK]   POST /v1/chat/completions — inference works on iMac"
else
  echo "[FAIL] chat inference: ${CHAT_RESP:0:300}"
  echo "       Fix Ollama before Cursor UI steps."
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  MANUAL STEPS (only you can do these in Cursor UI)           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  1. BOTTOM-RIGHT: click 'Cloud' → switch to LOCAL"
echo "     ✓ Cloud icon MUST disappear"
echo ""
echo "  2. Settings → Models → remove old custom models / tunnel URLs"
echo ""
echo "  3. + Add Custom Model:"
echo "       Model name : ${MODEL}"
echo "       Base URL   : ${LOCAL_BASE}"
echo "       API Key    : ollama"
echo "     → Click Verify (expect green checkmark)"
echo ""
echo "  4. Composer dropdown: select '${MODEL}'"
echo "     ✓ NOT 'Composer 2.5 Fast'"
echo ""
echo "=== Confirmation checklist (reply when done) ==="
echo "  [ ] Cloud icon gone"
echo "  [ ] Verify green in Settings → Models"
echo "  [ ] Composer shows: ${MODEL}"
echo "  [ ] Test message 'привет' gets a reply"
echo ""
