#!/usr/bin/env bash
# check-cursor-agent.sh — verify Cursor Cloud Agent by bcId (run on Mac with Cursor CLI)
# Usage:
#   bash scripts/check-cursor-agent.sh
#   bash scripts/check-cursor-agent.sh bc-a3990719-e6f2-484e-a3e7-3579dceba59e
set -euo pipefail

BC_ID="${1:-bc-a3990719-e6f2-484e-a3e7-3579dceba59e}"
AGENT_URL="https://cursor.com/agents/${BC_ID}"
DASHBOARD_URL="https://cursor.com/dashboard/cloud-agents"
LOCAL_AGENT_DIR="${HOME}/.cursor/agents"

echo "=== Cursor Cloud Agent Check ==="
echo "bcId:  ${BC_ID}"
echo "URL:   ${AGENT_URL}"
echo "Time:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

FAIL=0
ok()   { echo "[OK]   $*"; }
bad()  { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }
warn() { echo "[WARN] $*"; }
note() { echo "[INFO] $*"; }

# 1. Cursor CLI
if command -v cursor >/dev/null 2>&1; then
  ok "cursor CLI found: $(command -v cursor)"
  cursor --version 2>/dev/null | head -1 || true
else
  warn "cursor CLI not in PATH — install/update Cursor Desktop or add CLI to PATH"
fi

# 2. agents list (try both spellings — CLI varies by version)
FOUND_IN_LIST=0
if command -v cursor >/dev/null 2>&1; then
  for sub in "agents list" "agent list"; do
    note "Trying: cursor ${sub}"
    if OUT=$(cursor ${sub} 2>&1); then
      echo "$OUT" | head -30
      if echo "$OUT" | grep -qi "${BC_ID}"; then
        ok "bcId found in: cursor ${sub}"
        FOUND_IN_LIST=1
      fi
    else
      warn "cursor ${sub} failed or unsupported"
    fi
    echo ""
  done
fi

# 3. agents inspect
INSPECT_OK=0
if command -v cursor >/dev/null 2>&1; then
  for sub in "agents inspect" "agent inspect"; do
    note "Trying: cursor ${sub} ${BC_ID}"
    if OUT=$(cursor ${sub} "${BC_ID}" 2>&1); then
      if [[ -n "${OUT//[[:space:]]/}" ]]; then
        echo "$OUT"
        INSPECT_OK=1
        ok "inspect returned data"
      else
        warn "inspect empty output (${sub})"
      fi
    else
      warn "${sub} failed"
    fi
    echo ""
  done
fi

# 4. Local ~/.cursor/agents (hexstrike-executor etc. — NOT cloud bcId)
note "Local agent definitions: ${LOCAL_AGENT_DIR}"
if [[ -d "${LOCAL_AGENT_DIR}" ]]; then
  ls -la "${LOCAL_AGENT_DIR}" 2>/dev/null | head -15 || true
  if [[ -f "${LOCAL_AGENT_DIR}/hexstrike-executor.md" ]]; then
    note "hexstrike-executor.md exists (local prompt — different from Cloud bcId)"
  fi
else
  warn "No ${LOCAL_AGENT_DIR} — local custom agents not configured"
fi
echo ""

# 5. HTTP probe (often blank without auth cookie — expected)
note "HTTP probe (no session cookie — may timeout or return shell only)"
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 8 "${AGENT_URL}" 2>/dev/null || echo "000")
if [[ "${HTTP_CODE}" == "200" ]]; then
  ok "HTTP ${HTTP_CODE} — page reachable (content may still need login)"
elif [[ "${HTTP_CODE}" == "000" ]]; then
  warn "HTTP timeout/unreachable from this network — common; use Cursor IDE My Agents"
else
  note "HTTP ${HTTP_CODE}"
fi
echo ""

# 6. Interpretation
echo "=== Interpretation ==="
if [[ "${FOUND_IN_LIST}" -eq 1 || "${INSPECT_OK}" -eq 1 ]]; then
  ok "Agent visible to CLI — likely ACTIVE under your account"
elif command -v cursor >/dev/null 2>&1; then
  bad "bcId NOT in CLI list — deleted, wrong account, or CLI API mismatch"
else
  warn "Cannot confirm via CLI — open Cursor IDE → Agents → My Agents"
fi

echo ""
echo "Manual checks:"
echo "  1. Cursor IDE → Agents → My Agents → search ${BC_ID}"
echo "  2. Logged in as: monolit1984@icloud.com (owner of this run)"
echo "  3. Dashboard: ${DASHBOARD_URL}"
echo "  4. Blank web page ≠ deleted agent if session still answers in chat"
echo ""
echo "Inside an active Cloud Agent run, API reports:"
echo "  status=RUNNING isKilled=false → session alive even if web UI blank"
echo ""

exit "${FAIL}"
