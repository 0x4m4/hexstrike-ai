#!/usr/bin/env bash
# HexStrike — launch ALL available tools & workflows (read-only / authorized scope)
# Usage:
#   bash scripts/run-all-tools.sh                    # full local run
#   bash scripts/run-all-tools.sh --server-only      # start API + health only
#   bash scripts/run-all-tools.sh --skip-forensics   # skip 7-module forensics (~10min)
#   TARGET=http://51.250.97.223:8080 bash scripts/run-all-tools.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET="${TARGET:-http://51.250.97.223:8080}"
JENKINS="${JENKINS_TARGET:-http://51.250.97.223:8080}"
SERVER_URL="${HEXSTRIKE_URL:-http://127.0.0.1:8888}"
PORT="${HEXSTRIKE_PORT:-8888}"
LOG_DIR="$ROOT/artifacts/run-all-tools"
mkdir -p "$LOG_DIR"

SKIP_FORENSICS=0
SERVER_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --skip-forensics) SKIP_FORENSICS=1 ;;
    --server-only) SERVER_ONLY=1 ;;
  esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[run-all]${NC} $*"; }
ok()   { echo -e "${GREEN}OK${NC} $*"; }
warn() { echo -e "${YELLOW}WARN${NC} $*"; }
fail() { echo -e "${RED}FAIL${NC} $*"; }

# ── 0. Python env ──────────────────────────────────────────────
if [[ -f "$ROOT/hexstrike_env/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/hexstrike_env/bin/activate"
elif [[ -f "$ROOT/scripts/forensics-env-vps.sh" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/scripts/forensics-env-vps.sh" 2>/dev/null || true
elif [[ -f "$ROOT/scripts/forensics-env-mac.sh" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/scripts/forensics-env-mac.sh" 2>/dev/null || true
fi

# ── 1. Start hexstrike_server if not running ───────────────────
start_server() {
  if curl -sf --max-time 3 "$SERVER_URL/health" >/dev/null 2>&1; then
    ok "hexstrike_server already up at $SERVER_URL"
    return 0
  fi
  if command -v systemctl >/dev/null 2>&1 && systemctl is-enabled hexstrike-server >/dev/null 2>&1; then
    log "Starting via systemctl hexstrike-server ..."
    systemctl start hexstrike-server 2>/dev/null || true
    sleep 2
    if curl -sf --max-time 3 "$SERVER_URL/health" >/dev/null 2>&1; then
      ok "hexstrike_server via systemd"
      return 0
    fi
  fi
  log "Starting hexstrike_server on :$PORT (nohup) ..."
  nohup python3 "$ROOT/hexstrike_server.py" >> "$LOG_DIR/hexstrike-server.log" 2>&1 &
  local i
  for i in $(seq 1 30); do
    if curl -sf --max-time 2 "$SERVER_URL/health" >/dev/null 2>&1; then
      ok "hexstrike_server started (pid $(pgrep -f hexstrike_server.py | head -1))"
      return 0
    fi
    sleep 1
  done
  fail "hexstrike_server did not start — see $LOG_DIR/hexstrike-server.log"
  return 1
}

# ── 2. Tool inventory from /health ─────────────────────────────
tool_inventory() {
  log "Tool inventory via GET /health"
  curl -sf "$SERVER_URL/health" | python3 -c "
import json,sys
d=json.load(sys.stdin)
ts=d.get('tools_status',{})
avail=[k for k,v in ts.items() if v]
print(f\"Total installed: {d.get('total_tools_available',0)}/{d.get('total_tools_count',0)}\")
for cat, st in d.get('category_stats',{}).items():
    print(f\"  {cat}: {st.get('available',0)}/{st.get('total',0)}\")
open('$LOG_DIR/tools-available.txt','w').write('\n'.join(sorted(avail)))
" | tee "$LOG_DIR/tool-inventory.txt"
}

# ── 3. Orchestrator workflows (Python agents — always available) ─
run_orchestrator() {
  log "=== Orchestrator workflows ==="
  python3 scripts/hexstrike-orchestrator.py workflows | tee "$LOG_DIR/workflows-list.txt"

  local wf failed=0
  for wf in \
    infra-passive \
    defensive-disclosure \
    entity-id-pipeline \
    vps-full-readonly \
    hot-wallet-ops \
    operator-lab; do
    log "Workflow: $wf"
    if python3 scripts/hexstrike-orchestrator.py run "$wf" --quiet >> "$LOG_DIR/wf-${wf}.log" 2>&1; then
      ok "workflow $wf"
    else
      warn "workflow $wf — see $LOG_DIR/wf-${wf}.log"
      failed=$((failed + 1))
    fi
  done
  echo "$failed" > "$LOG_DIR/orchestrator-failed.count"
}

# ── 4. Shell pipelines ─────────────────────────────────────────
run_shell_pipelines() {
  log "=== Shell pipelines ==="

  log "Web pentest (IDOR/fuzz/SQLi)"
  bash scripts/run-web-app-pentest.sh "$JENKINS" >> "$LOG_DIR/web-pentest.log" 2>&1 && ok web-pentest || warn web-pentest

  log "Monitor combat readiness (sample)"
  export MONITOR_HEARTBEAT_POLLS=5 MONITOR_READINESS_SAMPLE_SEC=15
  bash scripts/monitor-combat-readiness.sh >> "$LOG_DIR/monitor-readiness.log" 2>&1 && ok monitor-readiness || warn monitor-readiness

  log "Payroll/OTC close (read-only verdict)"
  bash scripts/run-payroll-otc-close.sh >> "$LOG_DIR/payroll-close.log" 2>&1 && ok payroll-close || warn payroll-close

  if [[ "$SKIP_FORENSICS" -eq 0 ]]; then
    log "All forensics modules (7)"
    bash scripts/run-all-forensics.sh >> "$LOG_DIR/forensics-all.log" 2>&1 && ok forensics-all || warn forensics-all
  else
    warn "Skipping forensics (--skip-forensics)"
  fi
}

# ── 5. HexStrike API workflows (via CLI) ───────────────────────
run_api_workflows() {
  log "=== HexStrike API workflows on $TARGET ==="
  local cli="python3 hexstrike_cli.py --server $SERVER_URL"

  for cmd in \
    "technology-detect $TARGET" \
    "recon-workflow $TARGET" \
    "vulnerability-hunt $TARGET" \
    "business-logic-test $TARGET" \
    "nuclei-scan $TARGET --templates cves"; do
    log "CLI: $cmd"
    if $cli $cmd >> "$LOG_DIR/cli-${cmd// /-}.log" 2>&1; then
      ok "$cmd"
    else
      warn "$cmd — see logs"
    fi
  done
}

# ── 6. External tools via API (only if installed) ──────────────
run_installed_api_tools() {
  log "=== External tools via /api/tools/* (installed only) ==="
  local avail_file="$LOG_DIR/tools-available.txt"
  [[ -f "$avail_file" ]] || return 0

  run_tool() {
    local name="$1" endpoint="$2" payload="$3"
    grep -qx "$name" "$avail_file" || { warn "skip $name (not installed)"; return 0; }
    log "API tool: $name → $TARGET"
    curl -sf -X POST "$SERVER_URL$endpoint" \
      -H 'Content-Type: application/json' \
      -d "$payload" >> "$LOG_DIR/tool-${name}.log" 2>&1 && ok "$name" || warn "$name failed"
  }

  run_tool httpx    "/api/tools/httpx"    "{\"target\":\"$TARGET\",\"probe\":true}"
  run_tool nuclei   "/api/tools/nuclei"   "{\"target\":\"$TARGET\",\"severity\":\"critical,high\"}"
  run_tool nikto    "/api/tools/nikto"    "{\"target\":\"$TARGET\"}"
  run_tool ffuf     "/api/tools/ffuf"     "{\"url\":\"$TARGET\",\"mode\":\"directory\",\"match_codes\":\"200,301,302,403\"}"
  run_tool arjun    "/api/tools/arjun"    "{\"target\":\"$TARGET\",\"method\":\"GET,POST\"}"
  run_tool sqlmap   "/api/tools/sqlmap"   "{\"target\":\"$TARGET/login\",\"batch\":true,\"level\":1,\"risk\":1}"
  run_tool nmap     "/api/tools/nmap"     "{\"target\":\"51.250.97.223\",\"scan_type\":\"-sV -p 8080\"}"
  run_tool subfinder "/api/tools/subfinder" "{\"domain\":\"$(echo "$TARGET" | sed -E 's|https?://||; s|:.*||; s|/.*||')\"}"
}

# ── 7. Summary ─────────────────────────────────────────────────
write_summary() {
  local summary="$LOG_DIR/SUMMARY.md"
  cat > "$summary" << EOF
# HexStrike run-all-tools — $(date -u +%Y-%m-%dT%H:%M:%SZ)

**Target:** $TARGET  
**Server:** $SERVER_URL  
**Logs:** $LOG_DIR/

## Quick commands

| What | How |
|------|-----|
| Start API server | \`python3 hexstrike_server.py\` |
| List workflows | \`python3 scripts/hexstrike-orchestrator.py workflows\` |
| Full VPS chain | \`python3 scripts/hexstrike-orchestrator.py run-all\` |
| Web pentest | \`bash scripts/run-web-app-pentest.sh $JENKINS\` |
| Monitor readiness | \`bash scripts/monitor-combat-readiness.sh\` |
| All forensics | \`bash scripts/run-all-forensics.sh\` |
| 3 progons | \`bash scripts/run-three-progons.sh\` |
| Hot wallet ops | \`bash scripts/run-hot-wallet-ops.sh\` |
| Tool health | \`curl -s $SERVER_URL/health \| python3 -m json.tool\` |
| Autonomous monitor | \`python3 -u scripts/autonomous_monitor.py\` |

## Orchestrator workflows ($(grep -c . "$LOG_DIR/workflows-list.txt" 2>/dev/null || echo "?"))

See \`$LOG_DIR/wf-*.log\`

## Tool inventory

\$(cat "$LOG_DIR/tool-inventory.txt" 2>/dev/null || echo "n/a")
EOF
  ok "Summary: $summary"
}

# ── Main ───────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  HexStrike run-all-tools                                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "Target: $TARGET"
echo ""

start_server
tool_inventory

if [[ "$SERVER_ONLY" -eq 1 ]]; then
  ok "Server-only mode complete"
  exit 0
fi

run_orchestrator
run_shell_pipelines
run_api_workflows
run_installed_api_tools
write_summary

echo ""
ok "DONE — logs in $LOG_DIR/"
echo "  cat $LOG_DIR/SUMMARY.md"
echo "  cat $LOG_DIR/tool-inventory.txt"
