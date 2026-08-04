#!/usr/bin/env bash
# mcp-smoke-test.sh — read-only MCP bindings + RPC smoke test (Agent-Graph-01)
# Validates agent-bindings.json and performs defensive RPC probes only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BINDINGS="${MCP_BINDINGS:-$ROOT/mcp/agent-bindings.json}"
RPC_CONFIG="${HEXSTRIKE_RPC_CONFIG:-$ROOT/config/rpc_config.json}"
TARGET="${TARGET:-0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA}"
OUTPUT="${OUTPUT:-$ROOT/artifacts/mcp-smoke-report.json}"

pass=0
fail=0

ok()  { echo "[OK]   $*"; pass=$((pass + 1)); }
bad() { echo "[FAIL] $*"; fail=$((fail + 1)); }

rpc_call() {
  local url="$1" method="$2" params="${3:-[]}"
  curl -sf --max-time 10 -X POST "$url" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"params\":$params,\"id\":1}" 2>/dev/null || echo '{}'
}

echo "=== MCP Smoke Test (read-only) ==="
echo "Bindings: $BINDINGS"
echo "Target:   $TARGET"
echo "Time:     $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

if [[ ! -f "$BINDINGS" ]]; then
  bad "Bindings file missing: $BINDINGS"
  exit 1
fi
ok "Bindings file present"

python3 - <<'PY' "$BINDINGS" "$TARGET"
import json, sys
bindings_path, target = sys.argv[1], sys.argv[2].lower()
data = json.load(open(bindings_path))
assert data.get("agent") == "Agent-Graph-01", "agent mismatch"
assert data.get("target", "").lower() == target, "target mismatch in bindings"
servers = data.get("mcp_servers", {})
for name in ("evm-rpc-mcp", "block-explorer-mcp", "defi-dex-mcp"):
    assert name in servers, f"missing server: {name}"
routing = data.get("tool_routing", {})
assert "rpc_call_read" in routing, "rpc_call_read not routed"
print("[OK]   Bindings schema valid")
PY
pass=$((pass + 1))

if [[ ! -f "$RPC_CONFIG" ]]; then
  bad "RPC config missing: $RPC_CONFIG"
else
  ok "RPC config present"
  mapfile -t urls < <(python3 -c "
import json
c = json.load(open('$RPC_CONFIG'))
urls = [c.get('primary', '')] + list(c.get('fallbacks', []))
for u in urls:
    u = (u or '').strip()
    if u and u != 'REMOVED':
        print(u)
")
  rpc_ok=0
  chain_id=""
  for url in "${urls[@]}"; do
    resp="$(rpc_call "$url" "eth_chainId")"
    if echo "$resp" | grep -q '"result"'; then
      chain_id="$(echo "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('result',''))" 2>/dev/null || true)"
      ok "RPC eth_chainId via $url (chainId=$chain_id)"
      rpc_ok=1
      ACTIVE_RPC="$url"
      break
    else
      echo "[WARN] RPC unreachable: $url"
    fi
  done
  if [[ "$rpc_ok" -eq 0 ]]; then
    bad "No RPC endpoint responded"
  else
    bal_resp="$(rpc_call "$ACTIVE_RPC" "eth_getBalance" "[\"$TARGET\",\"latest\"]")"
    if echo "$bal_resp" | grep -q '"result"'; then
      ok "eth_getBalance for target"
    else
      bad "eth_getBalance failed"
    fi
    nonce_resp="$(rpc_call "$ACTIVE_RPC" "eth_getTransactionCount" "[\"$TARGET\",\"latest\"]")"
    if echo "$nonce_resp" | grep -q '"result"'; then
      ok "eth_getTransactionCount for target"
    else
      bad "eth_getTransactionCount failed"
    fi
    acct_resp="$(rpc_call "$ACTIVE_RPC" "eth_accounts")"
    if echo "$acct_resp" | grep -qE '"result"\s*:\s*\[\s*\]'; then
      ok "eth_accounts returns empty (no key exposure)"
    elif echo "$acct_resp" | grep -qE '"result"\s*:\s*\['; then
      bad "eth_accounts exposes accounts — CRITICAL RPC misconfiguration"
    else
      ok "eth_accounts blocked or unavailable (acceptable)"
    fi
  fi
fi

mkdir -p "$(dirname "$OUTPUT")"
export PASS="$pass" FAIL="$fail" OUTPUT ROOT="$ROOT" MCP_BINDINGS="$BINDINGS" TARGET="$TARGET"
python3 - <<'PY'
import json, os
from datetime import datetime, timezone

checks_passed = int(os.environ.get("PASS", "0"))
checks_failed = int(os.environ.get("FAIL", "0"))
out = os.environ["OUTPUT"]
bindings_path = os.environ.get("MCP_BINDINGS", os.path.join(os.environ.get("ROOT", "."), "mcp/agent-bindings.json"))
target = os.environ.get("TARGET", "")
if not target and os.path.isfile(bindings_path):
    try:
        target = json.load(open(bindings_path)).get("target", "")
    except (OSError, json.JSONDecodeError):
        pass
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "agent": "Agent-Graph-01",
    "task": "bind-mcp-tools",
    "mode": "read-only",
    "target": target,
    "bindings": os.environ.get("MCP_BINDINGS", "mcp/agent-bindings.json"),
    "checks_passed": checks_passed,
    "checks_failed": checks_failed,
    "success": checks_failed == 0,
}
with open(out, "w") as f:
    json.dump(report, f, indent=2)
print(json.dumps({"success": report["success"], "output": out, "checks_passed": checks_passed, "checks_failed": checks_failed}))
PY

echo ""
echo "Summary: passed=$pass failed=$fail"
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
exit 0
