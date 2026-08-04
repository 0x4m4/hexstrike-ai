#!/usr/bin/env bash
set -euo pipefail
PID_FILE="${TMPDIR:-/tmp}/hexstrike-interceptor.pid"
if [[ -f "$PID_FILE" ]]; then
  kill "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "[OK] Interceptor stopped"
else
  echo "[WARN] No interceptor pid file"
fi
