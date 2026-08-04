#!/usr/bin/env bash
# VPS: create/update .env with API keys (interactive or from env vars)
#
# Non-interactive:
#   ARKHAM_API_KEY=xxx GETBLOCK_API_KEY=yyy GITHUB_TOKEN=zzz bash scripts/vps-setup-env.sh
#
# Interactive:
#   bash scripts/vps-setup-env.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

log() { echo "[vps-env] $*"; }

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT/.env.example" "$ENV_FILE"
  log "Created $ENV_FILE from .env.example"
fi

_set_or_prompt() {
  local key="$1" prompt="$2" current=""
  current="$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
  if [[ -n "${!key:-}" ]]; then
    val="${!key}"
  elif [[ -t 0 ]]; then
    read -r -p "${prompt} [leave empty to keep current]: " val
    val="${val:-$current}"
  else
    val="$current"
  fi
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >>"$ENV_FILE"
  fi
}

_set_or_prompt ARKHAM_API_KEY "ARKHAM_API_KEY (entity labels)"
_set_or_prompt GETBLOCK_API_KEY "GETBLOCK_API_KEY (BSC RPC)"
_set_or_prompt GITHUB_TOKEN "GITHUB_TOKEN (OSINT code search)"
_set_or_prompt SHODAN_API_KEY "SHODAN_API_KEY (infra OSINT)"

if ! grep -qE '^HEXSTRIKE_API_KEY=.+' "$ENV_FILE" || grep -q 'change-me' "$ENV_FILE"; then
  key="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  if grep -qE '^HEXSTRIKE_API_KEY=' "$ENV_FILE"; then
    sed -i "s|^HEXSTRIKE_API_KEY=.*|HEXSTRIKE_API_KEY=${key}|" "$ENV_FILE"
  else
    echo "HEXSTRIKE_API_KEY=${key}" >>"$ENV_FILE"
  fi
  log "Generated HEXSTRIKE_API_KEY"
fi

chmod 600 "$ENV_FILE"
log "Updated $ENV_FILE (mode 600)"

# BSC RPC via GetBlock when key present
if grep -qE '^GETBLOCK_API_KEY=.+' "$ENV_FILE"; then
  gb="$(grep '^GETBLOCK_API_KEY=' "$ENV_FILE" | cut -d= -f2-)"
  if [[ -n "$gb" && "$gb" != "your-key" ]]; then
    if grep -qE '^BSC_RPC=' "$ENV_FILE"; then
      sed -i "s|^BSC_RPC=.*|BSC_RPC=https://go.getblock.io/${gb}/|" "$ENV_FILE"
    else
      echo "BSC_RPC=https://go.getblock.io/${gb}/" >>"$ENV_FILE"
    fi
    log "Set BSC_RPC from GETBLOCK_API_KEY"
  fi
fi

log "Restart services: systemctl restart hexstrike-orchestrator hexstrike-server"
