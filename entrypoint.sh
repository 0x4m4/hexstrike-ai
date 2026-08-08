#!/bin/bash
set -euo pipefail

# HEXSTRIKE_API_TOKEN is validated by the server itself (fails closed at
# import time if unset) — no need to duplicate that check here. This just
# gives a clearer error before Python even starts, and reports the scope
# state so a misconfigured engagement is obvious from `docker logs`.
if [ -z "${HEXSTRIKE_API_TOKEN:-}" ]; then
    echo "❌ HEXSTRIKE_API_TOKEN not set — refusing to start. Pass it via -e HEXSTRIKE_API_TOKEN=..." >&2
    exit 1
fi

if [ -z "${HEXSTRIKE_SCOPE_FILE:-}" ]; then
    echo "⚠️  HEXSTRIKE_SCOPE_FILE not set — scope enforcement is OFF. Do not point this at a real client engagement without it."
else
    echo "🎯 Scope enforcement active: ${HEXSTRIKE_SCOPE_FILE}"
fi

exec /opt/venv/bin/python3 hexstrike_server.py --host 0.0.0.0 --port 8888
