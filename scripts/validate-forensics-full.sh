#!/usr/bin/env bash
# Полная проверка forensics: workflow registry + 3 прогона (smoke)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== [1/4] validate workflows ==="
python3 scripts/validate-forensics-workflows.py

echo "=== [2/4] registry Agent-Forensics-01 ==="
python3 -c "
import json
r=json.load(open('agents/registry.json'))
assert 'Agent-Forensics-01' in r['agents']
assert 'run-analyzer-trx' in r['agents']['Agent-Forensics-01']['tasks']
print('[OK] Agent-Forensics-01 зарегистрирован')
"

echo "=== [3/4] operator-targets-3progon в workflows ==="
python3 -c "
import json
w=json.load(open('agents/workflows.json'))['workflows']
assert 'operator-targets-3progon' in w
print('[OK] workflow operator-targets-3progon')
"

echo "=== [4/4] три прогона ==="
export PATH=\"${HOME}/.foundry/bin:${PATH}\"
bash scripts/run-three-progons.sh

echo "=== validate-forensics-full: OK ==="
