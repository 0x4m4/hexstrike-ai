#!/usr/bin/env bash
# setup-cursor-ollama-mac.sh — operator Mac: Ollama + Cursor Qwen2.5-Coder integration
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/5] Setting OLLAMA_HOST in .env"
grep -q '^OLLAMA_HOST=' "$ROOT/.env" 2>/dev/null && \
  sed -i.bak 's|^OLLAMA_HOST=.*|OLLAMA_HOST=http://127.0.0.1:11434|' "$ROOT/.env" || \
  echo 'OLLAMA_HOST=http://127.0.0.1:11434' >> "$ROOT/.env"

if ! grep -q '^OLLAMA_ORIGINS=' "$ROOT/.env" 2>/dev/null; then
  echo 'OLLAMA_ORIGINS=*' >> "$ROOT/.env"
fi

export OLLAMA_HOST=http://127.0.0.1:11434
export OLLAMA_ORIGINS=*

echo "[2/5] Checking ollama CLI"
if ! command -v ollama &>/dev/null; then
  echo "Install: brew install ollama  OR  https://ollama.com/download"
  exit 1
fi

echo "[3/5] Pull qwen2.5-coder:7b if missing"
if ! ollama list 2>/dev/null | grep -q 'qwen2.5-coder:7b'; then
  ollama pull qwen2.5-coder:7b
fi

echo "[4/5] Ensure ollama serve is running"
if ! curl -sf --max-time 2 http://127.0.0.1:11434/api/tags &>/dev/null; then
  echo "Start Ollama app or run: ollama serve"
  exit 1
fi

echo "[5/5] Handshake verification"
"$ROOT/scripts/verify-ollama-handshake.sh"

echo ""
echo "=== Variant A — Local Autonomy (NO Cloud Agent) ==="
echo "Run the full runbook: ./scripts/variant-a-local-runbook.sh"
echo ""
echo "=== Cursor UI (manual — cannot be automated from repo) ==="
echo "1. Bottom-right: switch Cloud → LOCAL (Cloud icon must disappear)"
echo "2. Settings → Models → remove old models → + Add Custom Model"
echo "3. Model name: exact from 'ollama list' | Base URL: http://127.0.0.1:11434/v1 | API Key: ollama"
echo "4. Click Verify (green checkmark) → select model in Composer dropdown"
echo ""
echo "Project config: .cursor/settings.json"
