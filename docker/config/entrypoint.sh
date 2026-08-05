#!/usr/bin/env bash
# HexStrike MCP minimal entrypoint
# - Start server immediately
# - Background update of security databases (best-effort)

set -euo pipefail

log()       { printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&2; }
log_error() { printf '[%s] ERROR: %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&2; }

# --- Metasploit DB bootstrap (one-time, idempotent) ---
# Behavior:
# - If MSF_DB_URL is empty or unset, skip DB bootstrap (not an error).
# - If an active DB connection is already configured (db_status), skip bootstrap.
# - Otherwise, connect once and persist settings via db_save (stored under /root/.msf4).
if [ -z "${MSF_DB_URL:-}" ]; then
  log "[msf] MSF_DB_URL is not set; skipping Metasploit DB bootstrap."
else
  if ! command -v msfconsole >/dev/null 2>&1; then
    log_error "[msf] msfconsole not found in PATH; cannot bootstrap DB."
  else
    log "[msf] Checking current Metasploit DB status…"
    if msfconsole -qx 'db_status; exit -y' | grep -q 'Connected to'; then
      log "[msf] A data service is already configured; skipping bootstrap."
    else
      log "[msf] Initializing Metasploit DB config via db_connect…"
      mkdir -p /root/.msf4
      if msfconsole -qx "db_connect ${MSF_DB_URL}; db_save; db_status; exit -y"; then
        log "[msf] Metasploit DB configured and persisted."
      else
        log_error "[msf] db_connect failed; leaving Metasploit unconfigured."
      fi
    fi
  fi
fi

# --- Background updater (logs go to container stdout/stderr) ---
if command -v /usr/local/bin/update-tools-databases.sh >/dev/null 2>&1; then
  { /usr/local/bin/update-tools-databases.sh; } &
else
  log_error "[updater] /usr/local/bin/update-tools-databases.sh not found or not executable."
fi

# --- Start HexStrike MCP server ---
GUNICORN_BIN="/opt/hexstrike/venv/bin/gunicorn"
if [ ! -x "$GUNICORN_BIN" ]; then
  log_error "[server] gunicorn not found or not executable at ${GUNICORN_BIN}."
  exit 1
fi

log "[server] Starting HexStrike MCP server on 0.0.0.0:8888"
exec "$GUNICORN_BIN" \
  --bind 0.0.0.0:8888 \
  --workers 2 \
  --threads 8 \
  --timeout 3600 \
  --graceful-timeout 120 \
  --keep-alive 60 \
  "hexstrike_server:app"
