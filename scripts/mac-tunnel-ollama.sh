#!/usr/bin/env bash
# mac-tunnel-ollama.sh — expose local Ollama for Cursor Agents (private network bypass)
set -euo pipefail

PORT="${OLLAMA_PORT:-11434}"
URL="http://127.0.0.1:${PORT}"

echo "=== Ollama tunnel for Cursor (127.0.0.1 blocked in Agents) ==="

if ! curl -sf --max-time 3 "${URL}/api/tags" >/dev/null; then
  echo "[FAIL] Ollama not running. Run: open -a Ollama"
  exit 1
fi
echo "[OK]   Ollama at ${URL}"

try_cloudflared() {
  command -v cloudflared >/dev/null || return 1
  echo ""
  echo "--- Trying cloudflared (Ctrl+C to try next) ---"
  cloudflared tunnel --url "${URL}" 2>&1
}

try_ngrok() {
  command -v ngrok >/dev/null || return 1
  echo ""
  echo "--- Trying ngrok ---"
  ngrok http "${PORT}"
}

try_localtunnel() {
  command -v npx >/dev/null || return 1
  echo ""
  echo "--- Trying localtunnel ---"
  npx --yes localtunnel --port "${PORT}"
}

echo ""
echo "Pick method:"
echo "  1) cloudflared   brew install cloudflared"
echo "  2) ngrok         brew install ngrok"
echo "  3) localtunnel   needs node/npx"
echo ""
echo "When you get https://XXXX URL, set in Cursor Settings → Models:"
echo "  Base URL: https://XXXX/v1"
echo "  Model: deepseek-r1:1.5b"
echo "  API Key: ollama"
echo ""

METHOD="${1:-cloudflared}"
case "$METHOD" in
  cloudflared) try_cloudflared || { echo "[FAIL] cloudflared failed (error 1101 = retry later)"; exit 1; } ;;
  ngrok)       try_ngrok || die "ngrok not installed" ;;
  localtunnel) try_localtunnel ;;
  *)           try_cloudflared || try_ngrok || try_localtunnel ;;
esac
