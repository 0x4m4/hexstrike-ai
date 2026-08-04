#!/usr/bin/env bash
# switch-to-1.5b.sh — one-shot switch to deepseek-r1:1.5b (run on Mac)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="deepseek-r1:1.5b"
HOST="http://127.0.0.1:11434"
BASE="${HOST}/v1"

echo "=== Switching HexStrike → ${MODEL} ==="

command -v ollama >/dev/null || { echo "[FAIL] brew install ollama"; exit 1; }

if ! curl -sf --max-time 3 "${HOST}/api/tags" >/dev/null; then
  echo "[FAIL] Ollama not running. Start: ollama serve"
  exit 1
fi

if ! ollama list | grep -q "${MODEL}"; then
  echo "[pull] ${MODEL} ..."
  ollama pull "${MODEL}"
fi

touch "$ROOT/.env"
upsert() {
  local k="$1" v="$2"
  grep -q "^${k}=" "$ROOT/.env" && sed -i.bak "s|^${k}=.*|${k}=${v}|" "$ROOT/.env" || echo "${k}=${v}" >> "$ROOT/.env"
}

upsert "LLM_MODEL" "${MODEL}"
upsert "OLLAMA_MODEL" "${MODEL}"
upsert "OLLAMA_HOST" "${HOST}"
upsert "OLLAMA_PUBLIC_BASE_URL" "${BASE}"
upsert "OLLAMA_BYPASS_TUNNEL" "true"
upsert "OLLAMA_NUM_THREAD" "16"
upsert "OLLAMA_NUM_PREDICT" "256"
upsert "CURSOR_INTEGRATION_MODE" "OFFLINE_PRIMARY"

export LLM_MODEL="$MODEL" OLLAMA_MODEL="$MODEL"

python3 - "$ROOT/.cursor/settings.json" "$MODEL" "$BASE" <<'PY'
import json, sys
from pathlib import Path
p, model, base = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
d = json.loads(p.read_text())
for key in ("chat", "composer", "maxMode"):
    d["cursor"][key]["defaultModel"] = model
d["ollama"]["model"] = model
d["cursor"]["models"]["custom"] = [{
    "id": model, "name": model,
    "provider": "openai-compatible",
    "model_type": "openai_compatible",
    "baseUrl": base,
    "supportsChainOfThought": True,
    "options": {"num_thread": 16, "num_predict": 256},
}]
d["cursor"]["openai"]["baseUrl"] = base
d["env"]["LLM_MODEL"] = model
p.write_text(json.dumps(d, indent=2) + "\n")
print(f"[OK]   .cursor/settings.json → {model}")
PY

echo ""
echo "=== Speed test ==="
START=$(python3 -c "import time; print(time.time())")
RESP=$(curl -sf --max-time 30 "${BASE}/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"stream\":false,\"options\":{\"num_thread\":16,\"num_predict\":50},\"messages\":[{\"role\":\"user\",\"content\":\"Say pong\"}]}")
END=$(python3 -c "import time; print(time.time())")
echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
m=d['choices'][0]['message']
print('[OK]   content:', m.get('content','').strip()[:80])
r=m.get('reasoning') or ''
if r: print('[OK]   reasoning:', r[:80]+'...')
"
ELAPSED=$(python3 -c "print(f'{$END - $START:.1f}')")
echo "[OK]   latency: ${ELAPSED}s"
echo ""
echo "=== Cursor UI (manual) ==="
echo "  Settings → Models → remove :latest → Add: ${MODEL}"
echo "  Base URL: ${BASE} | API Key: ollama | Verify"
echo "  Composer dropdown → ${MODEL}"
