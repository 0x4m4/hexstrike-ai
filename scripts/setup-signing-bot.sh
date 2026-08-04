#!/usr/bin/env bash
# Signing bot setup: .env + dry-run (+ optional live start)
# Mac:  cd /Volumes/Eva/mufasaai-storage/hexstrike-ai && bash scripts/setup-signing-bot.sh
# VPS:  cd /opt/hexstrike-ai && bash scripts/setup-signing-bot.sh
# Live: bash scripts/setup-signing-bot.sh --start  (needs BOT_PRIVATE_KEY in .env)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ENV_FILE="$ROOT/.env"
START=0
for arg in "$@"; do [[ "$arg" == "--start" ]] && START=1; done

log() { echo "[signing-bot] $*"; }

# venv
if [[ -f "$ROOT/hexstrike_env/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/hexstrike_env/bin/activate"
else
  python3 -m venv "$ROOT/hexstrike_env"
  # shellcheck source=/dev/null
  source "$ROOT/hexstrike_env/bin/activate"
  pip install -q --upgrade pip
  pip install -q 'flask>=2.3' 'requests>=2.31' 'psutil>=5.9' 'eth-account>=0.10'
fi

git pull origin master 2>/dev/null || true

if [[ ! -f "$ENV_FILE" ]]; then
  log "Creating .env from template"
  cat >"$ENV_FILE" <<'ENV'
CHAIN_ID=56
RPC_URL=https://bsc-dataseed.binance.org
DIRECT_RPC_URL=https://bsc-dataseed.binance.org
BOT_ADDRESS=0x85dB346BE1d9d5D8ec4F57acf0067FbE53a6E846
BOT_PRIVATE_KEY=
TARGET_WATCH_ADDRESS=0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA
FUNDER_ADDRESS=0x85dB346BE1d9d5D8ec4F57acf0067FbE53a6E846
ALLOWED_FUNDERS=0x85dB346BE1d9d5D8ec4F57acf0067FbE53a6E846
DRY_RUN=true
HARDENING_ENABLED=true
POLL_INTERVAL_SEC=10
ENV
  chmod 600 "$ENV_FILE"
  log "EDIT .env — paste BOT_PRIVATE_KEY, then re-run"
else
  log ".env exists"
fi

chmod +x scripts/sandbox/deploy-mainnet.sh
./scripts/sandbox/deploy-mainnet.sh dry-run

if [[ "$START" -eq 1 ]]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  if [[ -z "${BOT_PRIVATE_KEY:-}" ]]; then
    log "FAIL: BOT_PRIVATE_KEY empty — cannot --start"
    exit 1
  fi
  log "Starting live bot (DRY_RUN=${DRY_RUN:-true})"
  ./scripts/sandbox/deploy-mainnet.sh start
  ./scripts/sandbox/deploy-mainnet.sh status
fi

log "DONE — logs: ./scripts/sandbox/deploy-mainnet.sh logs"
