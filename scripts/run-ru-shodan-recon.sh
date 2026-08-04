#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] && set -a && source .env && set +a
exec python3 "$ROOT/scripts/hexstrike-orchestrator.py" run ru-shodan-recon "$@"
