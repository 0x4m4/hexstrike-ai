#!/usr/bin/env bash
# diagnose-cursor-local.sh — why Cursor shows "AI Model Not Found" (run on Mac)
set -euo pipefail

HOST="http://127.0.0.1:11434"
BASE="${HOST}/v1"
MODEL="${1:-deepseek-r1:1.5b}"

echo "=== HexStrike Cursor Local Diagnostic ==="
echo ""

fail=0
ok()   { echo "[OK]   $1"; }
bad()  { echo "[FAIL] $1"; fail=$((fail+1)); }
warn() { echo "[WARN] $1"; }

if curl -sf --max-time 3 "${HOST}/api/tags" >/dev/null; then
  ok "Ollama reachable at ${HOST}"
else
  bad "Ollama NOT running — open Ollama.app or: ollama serve"
fi

if curl -sf --max-time 5 "${BASE}/models" | grep -q "\"id\":\"${MODEL}\""; then
  ok "Model registered in Ollama: ${MODEL}"
else
  bad "Model '${MODEL}' NOT in ollama list — run: ollama pull ${MODEL}"
  echo "       Available:"
  curl -sf "${BASE}/models" | python3 -c "import sys,json; [print('         ',m['id']) for m in json.load(sys.stdin).get('data',[])]" 2>/dev/null || true
fi

CHAT=$(curl -sf --max-time 60 "${BASE}/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"stream\":false,\"options\":{\"num_predict\":16},\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}" 2>&1) || true

if echo "$CHAT" | grep -q '"content"'; then
  ok "Chat inference works for ${MODEL}"
  echo "       response: $(echo "$CHAT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message'].get('content','')[:60])" 2>/dev/null)"
else
  bad "Chat inference failed: ${CHAT:0:120}"
fi

echo ""
echo "=== Cursor UI checklist (manual) ==="
echo ""
echo "  PROBLEM: 'AI Model Not Found' = Cursor Cloud cannot reach localhost."
echo ""
echo "  FIX 1 — EXIT Cloud Agent completely:"
echo "    • Close this Cloud Agent tab/session"
echo "    • Open Cursor DESKTOP app on iMac (not cursor.com/agents)"
echo "    • File → Open Folder → hexstrike-ai"
echo "    • Bottom bar must NOT show 'Cloud'"
echo ""
echo "  FIX 2 — Settings → Cursor Settings → Models:"
echo "    • OpenAI API Key section:"
echo "        Override Base URL: ON"
echo "        Base URL: ${BASE}"
echo "        API Key: ollama"
echo "    • Click '+ Add model' and type EXACTLY:"
echo "        ${MODEL}"
echo "    • Click Verify → must be GREEN"
echo "    • Disable/remove: Composer 2.5, gpt-4, cloud models"
echo ""
echo "  FIX 3 — Composer dropdown:"
echo "    • Select: ${MODEL}"
echo "    • NOT 'Composer 2.5 Fast'"
echo ""
echo "  Model name must match ollama EXACTLY (case, colons, :latest tag)."
echo ""

if [[ $fail -eq 0 ]]; then
  echo "=== Backend OK — fix is 100% in Cursor UI (Cloud → Local) ==="
else
  echo "=== Fix Ollama first, then Cursor UI ==="
fi
exit "$fail"
