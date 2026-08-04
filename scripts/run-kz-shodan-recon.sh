#!/usr/bin/env bash
# Run Kazakhstan Shodan/OSINT agent workflow (read-only defensive IR)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] && set -a && source .env && set +a
exec python3 "$ROOT/scripts/hexstrike-orchestrator.py" run kz-shodan-recon "$@"
