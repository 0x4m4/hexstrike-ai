#!/usr/bin/env bash
# health_check.sh — verify RPC, Eva HDD mount, and HexStrike API availability
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CONFIG="${HEXSTRIKE_RPC_CONFIG:-$ROOT/config/rpc_config.json}"
EVA_MOUNT="${HEXSTRIKE_EVA_MOUNT:-/Volumes/Eva}"
ENV_FILE="$ROOT/.env"

failures=0
warnings=0

pass() { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; warnings=$((warnings + 1)); }
fail() { echo "[FAIL] $*"; failures=$((failures + 1)); }

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "$ENV_FILE" | grep -E '^(HEXSTRIKE_API_KEY|HEXSTRIKE_)' | xargs) 2>/dev/null || true
  fi
}

check_rpc() {
  echo "--- RPC connectivity ---"
  if [[ ! -f "$CONFIG" ]]; then
    fail "RPC config not found: $CONFIG"
    return
  fi

  local primary fallbacks url
  primary="$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c.get('primary',''))")"
  fallbacks="$(python3 -c "import json; c=json.load(open('$CONFIG')); print(','.join(c.get('fallbacks',[])))")"

  if [[ -z "$primary" ]]; then
    fail "No primary RPC URL in $CONFIG"
    return
  fi

  local urls=("$primary")
  if [[ -n "$fallbacks" ]]; then
    IFS=',' read -r -a extra <<< "$fallbacks"
    urls+=("${extra[@]}")
  fi

  local any_ok=0
  for url in "${urls[@]}"; do
    url="$(echo "$url" | xargs)"
    [[ -z "$url" ]] && continue
    if curl -sf --max-time 8 -X POST "$url" \
      -H 'Content-Type: application/json' \
      -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' \
      | grep -q '"result"'; then
      pass "RPC reachable: $url"
      any_ok=1
      break
    else
      warn "RPC unreachable: $url"
    fi
  done

  if [[ "$any_ok" -eq 0 ]]; then
    fail "No RPC endpoints responded"
  fi
}

check_eva_mount() {
  echo "--- Eva HDD mount ---"
  if [[ "$(uname -s)" != "Darwin" ]]; then
    warn "Eva mount check skipped (not macOS): $EVA_MOUNT"
    return
  fi

  if mount | grep -q " on ${EVA_MOUNT} "; then
    pass "Eva HDD mounted at $EVA_MOUNT"
    if [[ -w "$EVA_MOUNT" ]]; then
      pass "Eva mount is writable"
    else
      warn "Eva mount is read-only: $EVA_MOUNT"
    fi
  else
    fail "Eva HDD not mounted at $EVA_MOUNT"
  fi
}

check_api() {
  echo "--- HexStrike API ---"
  load_env

  local server api_key
  server="$(python3 -c "
import json
c = json.load(open('$CONFIG'))
print(c.get('hexstrike_api', {}).get('server', 'http://127.0.0.1:8888'))
")"
  api_key="${HEXSTRIKE_API_KEY:-}"

  if [[ -z "$api_key" ]]; then
    fail "HEXSTRIKE_API_KEY not set (configure $ENV_FILE)"
    return
  fi

  local status body
  status="$(curl -s -o /tmp/hexstrike_health_body.json -w '%{http_code}' --max-time 10 \
    -H "X-API-KEY: $api_key" \
    "${server%/}/api/context/latest" || echo "000")"

  case "$status" in
    200)
      pass "API reachable: ${server%/}/api/context/latest (HTTP 200)"
      if grep -q '"entries"' /tmp/hexstrike_health_body.json 2>/dev/null; then
        pass "API context payload looks valid"
      else
        warn "API returned 200 but context shape unexpected"
      fi
      ;;
    403)
      fail "API forbidden (invalid API key?)"
      ;;
    000)
      fail "API unreachable: $server"
      ;;
    *)
      fail "API returned HTTP $status"
      ;;
  esac
}

main() {
  echo "HexStrike health check — $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  check_rpc
  check_eva_mount
  check_api
  echo "---"
  echo "Summary: failures=$failures warnings=$warnings"
  if [[ "$failures" -gt 0 ]]; then
    exit 1
  fi
  exit 0
}

main "$@"
