#!/usr/bin/env bash
# vps-start-ollama.sh — install + expose Ollama on HexStrike VPS (78.27.235.70)
#
# Run ON VPS as root:
#   bash scripts/vps-start-ollama.sh
#
# Or one-liner from phone SSH (Termius):
#   curl -fsSL https://raw.githubusercontent.com/Banda198565/hexstrike-ai/master/scripts/vps-start-ollama.sh | bash
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
PORT="${OLLAMA_PORT:-11434}"
LOG="/var/log/hexstrike/ollama.log"

log()  { echo "[vps-ollama] $*"; }
ok()   { echo "[vps-ollama] OK: $*"; }
warn() { echo "[vps-ollama] WARN: $*"; }
die()  { echo "[vps-ollama] ERROR: $*" >&2; exit 1; }

[[ $(id -u) -eq 0 ]] || die "Run as root on VPS: ssh root@78.27.235.70"

mkdir -p /var/log/hexstrike

# ── 1. Install Ollama ───────────────────────────────────────────
if ! command -v ollama >/dev/null 2>&1; then
  log "Installing Ollama..."
  command -v zstd >/dev/null 2>&1 || apt-get update -qq && apt-get install -y -qq zstd curl
  curl -fsSL https://ollama.com/install.sh | sh
fi
ok "ollama $(ollama --version 2>/dev/null || echo installed)"

# ── 2. systemd override — listen on all interfaces ──────────────
mkdir -p /etc/systemd/system/ollama.service.d
cat >/etc/systemd/system/ollama.service.d/override.conf <<EOF
[Service]
Environment="OLLAMA_HOST=0.0.0.0:${PORT}"
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_LLM_LIBRARY=cpu_avx2"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
EOF

systemctl daemon-reload
systemctl enable ollama 2>/dev/null || true
systemctl restart ollama
sleep 4

if ! curl -sf --max-time 5 "http://127.0.0.1:${PORT}/api/tags" >/dev/null; then
  warn "systemd ollama failed — fallback: nohup serve"
  pkill -f 'ollama serve' 2>/dev/null || true
  nohup env OLLAMA_HOST="0.0.0.0:${PORT}" OLLAMA_ORIGINS='*' OLLAMA_LLM_LIBRARY=cpu_avx2 \
    ollama serve >>"$LOG" 2>&1 &
  sleep 4
fi

curl -sf --max-time 8 "http://127.0.0.1:${PORT}/api/tags" >/dev/null \
  || die "Ollama not responding on 127.0.0.1:${PORT}"

ok "Ollama API up on 0.0.0.0:${PORT}"

# ── 3. Pull coding model ────────────────────────────────────────
if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
  log "Pulling ${MODEL} (may take a few minutes)..."
  ollama pull "$MODEL"
fi
ok "Model ready: ${MODEL}"

# ── 4. Firewall (best effort) ───────────────────────────────────
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q active; then
  ufw allow "${PORT}/tcp" 2>/dev/null || true
  ok "ufw allow ${PORT}/tcp"
fi

# ── 5. Health check ─────────────────────────────────────────────
TAGS="$(curl -sf "http://127.0.0.1:${PORT}/api/tags")"
MODELS="$(curl -sf "http://127.0.0.1:${PORT}/v1/models")"

echo ""
echo "════════════════════════════════════════════════════════"
echo " Ollama on VPS — READY"
echo "════════════════════════════════════════════════════════"
echo " Local:   http://127.0.0.1:${PORT}/v1"
echo " Phone:   http://78.27.235.70:${PORT}/v1"
echo " API Key: ollama"
echo " Model:   ${MODEL}"
echo ""
echo " Phone app settings:"
echo "   Host:    http://78.27.235.70:${PORT}/v1"
echo "   API Key: ollama"
echo ""
echo " Test from phone Safari:"
echo "   http://78.27.235.70:${PORT}/v1/models"
echo "════════════════════════════════════════════════════════"

python3 - <<PY
import json
tags = json.loads('''${TAGS}''')
models = json.loads('''${MODELS}''')
print("Installed:", [m.get("name") for m in tags.get("models", [])])
print("OpenAI /v1:", [m.get("id") for m in models.get("data", [])])
PY
