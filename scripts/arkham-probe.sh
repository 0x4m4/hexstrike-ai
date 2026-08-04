#!/usr/bin/env bash
# arkham-probe.sh — read-only Arkham API smoke test for hot wallet entity ID
# Docs: https://intel.arkm.com/api/docs  |  https://api.arkm.com (OpenAPI)
# Usage:
#   ARKHAM_API_KEY=xxx bash scripts/arkham-probe.sh
#   ARKHAM_API_KEY=xxx bash scripts/arkham-probe.sh 0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] && set -a && source .env && set +a

TARGET="${1:-0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA}"
CHAINS="${ARKHAM_CHAINS:-ethereum,bsc,polygon,base,arbitrum}"
CHAIN="${ARKHAM_CHAIN:-bsc}"

echo "=== Arkham API Probe (read-only) ==="
echo "Target: $TARGET"
echo "Time:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

if [[ -z "${ARKHAM_API_KEY:-}" ]]; then
  echo "[FAIL] ARKHAM_API_KEY not set"
  echo ""
  echo "1. Request access: https://arkm.com/api"
  echo "2. Add to .env:     ARKHAM_API_KEY=your_key"
  echo "3. Re-run:          bash scripts/arkham-probe.sh"
  echo ""
  echo "Manual UI (no key): https://platform.arkhamintelligence.com/explorer/address/${TARGET}"
  exit 1
fi

export TARGET CHAINS CHAIN
python3 - <<'PY'
import json, os, sys
sys.path.insert(0, "scripts/agents")
from arkham_client import (
    ArkhamError,
    get_address_balances,
    get_address_enriched,
    get_credit_periods,
    health_check,
    summarize_balances,
    summarize_intel,
)

target = os.environ["TARGET"]
chains = os.environ["CHAINS"]
chain = os.environ["CHAIN"]
fail = 0

def ok(name, detail):
    print(f"[OK]   {name} — {detail}")

def bad(name, detail):
    global fail
    print(f"[FAIL] {name} — {detail}")
    fail += 1

healthy, health_msg = health_check()
if healthy:
    ok("health", health_msg)
else:
    bad("health", f"{health_msg} — Arkham API may be down (502/timeout); retry in a few minutes")

try:
    intel = get_address_enriched(target, chain)
    s = summarize_intel(intel)
    ok("address_enriched", json.dumps(s, ensure_ascii=False))
    if s.get("entity_name"):
        ok("entity_resolved", f"{s['entity_name']} ({s.get('entity_id')})")
    else:
        print("[WARN] No Arkham entity label — wallet may be unlabeled")
except ArkhamError as e:
    bad("address_enriched", str(e))

try:
    bal = get_address_balances(target, chains)
    sb = summarize_balances(bal)
    ok("balances", json.dumps(sb, ensure_ascii=False))
except ArkhamError as e:
    bad("balances", str(e))

try:
    periods = get_credit_periods()
    current = next((p for p in periods if p.get("status") == "current"), periods[0] if periods else None)
    if current:
        ok("credit_periods", f"current: used={current.get('creditsUsed')}/{current.get('creditsIncluded')} extra={current.get('extraCredits')}")
    else:
        ok("credit_periods", f"{len(periods)} periods returned")
except ArkhamError as e:
    bad("credit_periods", str(e))

print("")
print(f"=== Summary: failures={fail} ===")
sys.exit(fail)
PY
