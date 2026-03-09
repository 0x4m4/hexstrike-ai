#!/usr/bin/env bash
# Update vulnerability/security tool databases for the HexStrike AI container.
# Scope: environment-only refresh steps (no scanning).


set -euo pipefail

log()       { printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&2; }
log_error() { printf '[%s] ERROR: %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&2; }

HOME="${HOME:-/root}"

log "=== HexStrike updater: starting ==="

# --- Sanity overview (missing => ERROR) ---
if [ -d "$HOME/.wpscan/db" ]; then
  log "WPScan DB dir:        ${HOME}/.wpscan/db  [present]"
else
  log_error "WPScan DB dir missing: ${HOME}/.wpscan/db"
fi

if [ -d "$HOME/.cache/trivy" ]; then
  log "Trivy cache dir:      ${HOME}/.cache/trivy  [present]"
else
  log_error "Trivy cache dir missing: ${HOME}/.cache/trivy"
fi

if [ -d "$HOME/nuclei-templates" ]; then
  log "Nuclei templates dir: ${HOME}/nuclei-templates  [present]"
else
  log_error "Nuclei templates dir missing: ${HOME}/nuclei-templates"
fi

if [ -d "/usr/share/exploitdb" ]; then
  log "ExploitDB dir:        /usr/share/exploitdb  [present]"
else
  log_error "ExploitDB dir missing: /usr/share/exploitdb"
fi

if [ -d "/var/lib/nikto" ]; then
  log "Nikto data dir:       /var/lib/nikto  [present]"
else
  log_error "Nikto data dir missing: /var/lib/nikto"
fi

if [ -f "/usr/share/nmap/scripts/script.db" ]; then
  log "Nmap scripts DB:      /usr/share/nmap/scripts/script.db  [present]"
else
  log_error "Nmap scripts DB missing: /usr/share/nmap/scripts/script.db"
fi

if [ -d "$HOME/.ZAP" ]; then
  log "ZAP home:             ${HOME}/.ZAP  [present]"
else
  log_error "ZAP home missing: ${HOME}/.ZAP (it will be created on first run)"
fi

# --- WPScan DB update ---
log "WPScan: updating vulnerability DB…"
if command -v wpscan >/dev/null 2>&1; then
  if ! wpscan --update; then
    log_error "WPScan DB update failed (non-zero exit)"
  fi
else
  log_error "WPScan binary not found in PATH"
fi

# --- Trivy DB download (no scan) ---
if command -v trivy >/dev/null 2>&1; then
  if ! trivy image --download-db-only --cache-dir "${HOME}/.cache/trivy"; then
    log_error "Trivy DB download failed (non-zero exit)"
  fi
else
  log_error "Trivy binary not found in PATH"
fi

# --- Nmap scripts DB refresh ---
log "Nmap: refreshing scripts database…"
if command -v nmap >/dev/null 2>&1; then
  if ! nmap --script-updatedb; then
    log_error "Nmap script-updatedb failed (non-zero exit)"
  fi
else
  log_error "Nmap binary not found in PATH"
fi

# --- OWASP ZAP add-ons (headless) ---
# Bind to a dedicated, non-conflicting port to avoid "Address already in use".
log "ZAP: updating add-ons (headless)…"
if command -v zaproxy >/dev/null 2>&1; then
  if ! zaproxy -cmd -silent -port 8099 -addonupdate; then
    log_error "ZAP add-on update failed (non-zero exit)"
  fi
else
  log_error "ZAP (zaproxy) binary not found in PATH"
fi

# --- Nuclei templates update ---
log "Nuclei: updating templates…"
if command -v nuclei >/dev/null 2>&1; then
  if ! nuclei -update-templates; then
    log_error "Nuclei templates update failed (non-zero exit)"
  fi
else
  log_error "Nuclei binary not found in PATH"
fi

log "=== HexStrike updater: done ==="
