#!/usr/bin/env bash
# 07-hardening-blocks-tamper.sh — simulated RPC mismatch must block hardened bot
set -euo pipefail
REDTEAM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX="$(cd "$REDTEAM/.." && pwd)"
# shellcheck source=_common.sh
source "$REDTEAM/_common.sh"

echo "=== REDTEAM 07: hardening vs tampered RPC (unit sim) ==="
# Run unit test with clean RPC env (anvil.env sets primary=direct and breaks the sim)
if env -u RPC_URL -u DIRECT_RPC_URL -u UPSTREAM_RPC \
  RPC_URL=http://127.0.0.1:8546 DIRECT_RPC_URL=http://127.0.0.1:8545 \
  python3 "$SANDBOX/test_attack_blocked.py" 2>&1 | grep -qiE "attack failed|NOT sign|BLOCKED"; then
  log_result "07-hardening-blocks-tamper" "DEFENDED" "rpc_mismatch blocked signing"
else
  log_result "07-hardening-blocks-tamper" "VULN_CONFIRMED" "hardening did not block tamper sim"
fi
