#!/usr/bin/env bash
# install-cursor-ollama-config.sh — install Ollama + ~/.cursor/config.json (Mac)
# Usage: bash scripts/install-cursor-ollama-config.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CURSOR_DIR="${HOME}/.cursor"
CONFIG_DST="${CURSOR_DIR}/config.json"
TEMPLATE="${ROOT}/scripts/cursor-ollama-config.json"
MODEL="${OLLAMA_MODEL:-deepseek-r1:1.5b}"
HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

echo "=== HexStrike: Ollama → Cursor config install ==="
echo ""

# 1. Ollama CLI
if command -v ollama >/dev/null 2>&1; then
  echo "[OK]   ollama CLI: $(command -v ollama)"
else
  echo "[WARN] ollama not found"
  echo "       brew install ollama"
  echo "       or: curl -fsSL https://ollama.com/install.sh | sh"
fi

# 2. Ollama serve
if curl -sf --max-time 3 "${HOST}/api/tags" >/dev/null 2>&1; then
  echo "[OK]   Ollama API: ${HOST}"
else
  echo "[WARN] Ollama not running — start: open -a Ollama  OR  ollama serve"
fi

# 3. Pull model
if command -v ollama >/dev/null 2>&1; then
  if ollama list 2>/dev/null | grep -q "${MODEL}"; then
    echo "[OK]   Model present: ${MODEL}"
  else
    echo "[INFO] Pulling ${MODEL} ..."
    ollama pull "${MODEL}" || echo "[WARN] pull failed — run manually: ollama pull ${MODEL}"
  fi
fi

# 4. Install ~/.cursor/config.json
mkdir -p "${CURSOR_DIR}"
if [[ -f "${CONFIG_DST}" ]]; then
  cp -a "${CONFIG_DST}" "${CONFIG_DST}.bak.$(date +%Y%m%d%H%M%S)"
  echo "[OK]   Backed up existing ${CONFIG_DST}"
fi
cp "${TEMPLATE}" "${CONFIG_DST}"
chmod 600 "${CONFIG_DST}" 2>/dev/null || true
echo "[OK]   Installed ${CONFIG_DST}"

# 5. Project .cursor/settings.json (repo integration mode)
if [[ -f "${ROOT}/scripts/enable-system-integration-mode.sh" ]]; then
  if curl -sf --max-time 3 "${HOST}/api/tags" >/dev/null 2>&1; then
    echo "[INFO] Running enable-system-integration-mode.sh ..."
    bash "${ROOT}/scripts/enable-system-integration-mode.sh" || true
  else
    echo "[SKIP] enable-system-integration-mode (Ollama down)"
  fi
fi

# 6. Project .env
touch "${ROOT}/.env"
for kv in \
  "OLLAMA_HOST=${HOST}" \
  "OLLAMA_ORIGINS=*" \
  "OLLAMA_PUBLIC_BASE_URL=${HOST}/v1" \
  "OLLAMA_BYPASS_TUNNEL=true" \
  "LLM_PROVIDER=ollama-local" \
  "LLM_BASE_URL=${HOST}/v1" \
  "LLM_MODEL=${MODEL}" \
  "CURSOR_INTEGRATION_MODE=OFFLINE_PRIMARY"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "${ROOT}/.env" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${kv}|" "${ROOT}/.env"
  else
    echo "${kv}" >> "${ROOT}/.env"
  fi
done
echo "[OK]   Updated ${ROOT}/.env"

echo ""
echo "=== Manual steps in Cursor IDE ==="
echo "1. Switch Cloud → LOCAL (bottom-right)"
echo "2. Settings → Models → Add Custom Model (if not auto-detected):"
echo "   Model:  ${MODEL}"
echo "   URL:    ${HOST}/v1"
echo "   API Key: ollama"
echo "3. Verify → select model in Composer"
echo ""
echo "Verify: bash scripts/verify-ollama-handshake.sh"
echo "Done."
