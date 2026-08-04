#!/usr/bin/env bash
set -euo pipefail
PID_FILE="${TMPDIR:-/tmp}/hexstrike-anvil.pid"
if [[ -f "$PID_FILE" ]]; then
  kill "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "[OK] Anvil stopped"
else
  echo "[WARN] No pid file — anvil may not be running"
fi
