#!/usr/bin/env bash
# run-battle-suite.sh — build Go agent and run full 7-attack battle (orchestrator entry)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="${HOME}/.foundry/bin:${PATH}"
bash "$ROOT/cmd/agent/build.sh"
exec "$ROOT/bin/hexstrike-agent" battle -v
