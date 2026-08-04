#!/usr/bin/env bash
# run-all.sh — local Anvil red-team suite (SANDBOX ONLY)
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX="$(cd "$REDTEAM/.." && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║  HexStrike Red-Team — LOCAL ANVIL SANDBOX ONLY   ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

"$SANDBOX/start-anvil.sh"
"$SANDBOX/setup-anvil-env.sh" 2>/dev/null || true

rm -f /workspace/artifacts/sandbox/redteam-report.json
mkdir -p /workspace/artifacts/sandbox
: > /workspace/artifacts/sandbox/dummy-bot-events.jsonl

for s in 01-baseline-trigger 02-race-duplicate-sign 03-front-run-drain \
         04-replay-rescue-tx 05-toctou-nonce-bump 06-compromised-funder \
         07-hardening-blocks-tamper; do
  echo ""
  "$SANDBOX/start-anvil.sh" >/dev/null 2>&1 || true
  "$REDTEAM/${s}.sh" || true
  kill "$(cat /tmp/redteam-bot.pid 2>/dev/null)" 2>/dev/null || true
  rm -f /tmp/redteam-bot.pid
done

echo ""
echo "=== SUMMARY ==="
python3 - /workspace/artifacts/sandbox/redteam-report.json <<'PY'
import json, sys
from collections import Counter
data = json.load(open(sys.argv[1]))
counts = Counter(r["outcome"] for r in data.get("runs", []))
for k, v in sorted(counts.items()):
    print(f"  {k}: {v}")
print("\nFull report:", sys.argv[1])
for r in data.get("runs", []):
    print(f"  • {r['scenario']}: {r['outcome']} — {r.get('detail','')}")
PY

"$SANDBOX/stop-anvil.sh" 2>/dev/null || true