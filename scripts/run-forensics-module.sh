#!/usr/bin/env bash
# Run a single forensics module: agent → analyzer → orchestrator workflow
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODULE="${1:?usage: run-forensics-module.sh <name> <agent> <task> <analyze-kind> <workflow>}"
AGENT="${2:?agent}"
TASK="${3:?task}"
ANALYZE="${4:?analyze-kind}"
WORKFLOW="${5:?workflow}"

export HEXSTRIKE_MODE="${HEXSTRIKE_MODE:-forensics}"

echo "=== HexStrike ${MODULE} Forensics ==="
echo "mode:         ${HEXSTRIKE_MODE}"
echo "hexstrike-ai: ${ROOT}"

echo "[1/3] ${AGENT}"
python3 scripts/hexstrike-agent.py --agent "$AGENT" --task "$TASK"

echo "[2/3] Orchestrator ${ANALYZE}-analyze"
python3 scripts/forensics/analyze.py "$ANALYZE"

echo "[3/3] Workflow ${WORKFLOW}"
python3 scripts/hexstrike-orchestrator.py run "$WORKFLOW" --quiet

echo "=== Done ${MODULE} ==="
