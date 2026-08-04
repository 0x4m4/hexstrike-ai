#!/usr/bin/env bash
# Run on Mac (source Redis). Dumps RDB and copies to HexStrike VPS over SSH.
#
# Usage:
#   REDIS_PASSWORD='your-mac-redis-password' bash scripts/redis-migrate-from-mac.sh
#   # no-auth local Redis:
#   ALLOW_EMPTY_REDIS_AUTH=1 bash scripts/redis-migrate-from-mac.sh
#   # tunneled Redis:
#   REDIS_HOST=127.0.0.1 REDIS_PORT=6380 bash scripts/redis-migrate-from-mac.sh
#
# Requires: redis-cli on Mac, working `ssh hexstrike-vps` (key auth).
set -euo pipefail

VPS_HOST="${VPS_HOST:-hexstrike-vps}"
LOCAL_RDB="${LOCAL_RDB:-/tmp/hexstrike_migration.rdb}"
REMOTE_RDB="${REMOTE_RDB:-/tmp/hexstrike_migration.rdb}"
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
AUTH="${REDISCLI_AUTH:-${REDIS_PASSWORD:-}}"

if [[ -z "$AUTH" && "${ALLOW_EMPTY_REDIS_AUTH:-0}" != "1" ]]; then
  echo "[migrate] ERROR: set REDIS_PASSWORD / REDISCLI_AUTH, or ALLOW_EMPTY_REDIS_AUTH=1 for no-auth Redis" >&2
  echo "  example: REDIS_PASSWORD='...' bash scripts/redis-migrate-from-mac.sh" >&2
  exit 1
fi

if [[ -n "$AUTH" ]]; then
  export REDISCLI_AUTH="$AUTH"
else
  unset REDISCLI_AUTH || true
fi

redis_cli() {
  # shellcheck disable=SC2086
  redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" "$@"
}

echo "[migrate] target redis ${REDIS_HOST}:${REDIS_PORT}"
MAC_REDIS_VER="$(redis_cli INFO server 2>/dev/null | awk -F: '/^redis_version:/{gsub(/\r/,"",$2); print $2}')"
if [[ -z "${MAC_REDIS_VER:-}" ]]; then
  echo "[migrate] ERROR: cannot reach Redis at ${REDIS_HOST}:${REDIS_PORT} (check host/port/auth)" >&2
  exit 1
fi
echo "[migrate] Mac redis_version=${MAC_REDIS_VER}"

echo "[migrate] dumping Mac redis -> $LOCAL_RDB"
redis_cli --rdb "$LOCAL_RDB"
ls -la "$LOCAL_RDB"
file "$LOCAL_RDB" || true

# Best-effort RDB magic / version note (REDIS000X in file header)
RDB_MAGIC="$(head -c 9 "$LOCAL_RDB" 2>/dev/null || true)"
echo "[migrate] RDB header: ${RDB_MAGIC:-unknown}"

VPS_REDIS_VER="$(ssh "$VPS_HOST" "redis-cli INFO server 2>/dev/null | awk -F: '/^redis_version:/{gsub(/\\r/,\"\",\$2); print \$2}'" || true)"
if [[ -n "${VPS_REDIS_VER:-}" ]]; then
  echo "[migrate] VPS redis_version=${VPS_REDIS_VER}"
  MAC_MAJOR="${MAC_REDIS_VER%%.*}"
  VPS_MAJOR="${VPS_REDIS_VER%%.*}"
  if [[ "$MAC_MAJOR" =~ ^[0-9]+$ && "$VPS_MAJOR" =~ ^[0-9]+$ && "$MAC_MAJOR" -gt "$VPS_MAJOR" ]]; then
    echo "[migrate] WARN: Mac Redis major ${MAC_MAJOR} > VPS major ${VPS_MAJOR}." >&2
    echo "[migrate] WARN: Loading a newer RDB on an older Redis often fails to start." >&2
    echo "[migrate] WARN: Upgrade VPS Redis or export/import with compatible versions before replacing dump.rdb." >&2
    if [[ "${FORCE_RDB_MIGRATE:-0}" != "1" ]]; then
      echo "[migrate] ERROR: refusing to copy incompatible RDB (set FORCE_RDB_MIGRATE=1 to override)" >&2
      exit 1
    fi
    echo "[migrate] FORCE_RDB_MIGRATE=1 — continuing despite version skew"
  fi
else
  echo "[migrate] WARN: could not read VPS redis_version — verify compatibility before replacing dump.rdb" >&2
fi

echo "[migrate] copying to ${VPS_HOST}:${REMOTE_RDB}"
SCP_OPTS=()
if scp 2>&1 | grep -q -- '-O'; then
  # OpenSSH 9+: prefer legacy SCP protocol for broader server compatibility when available
  SCP_OPTS+=(-O)
fi
scp "${SCP_OPTS[@]}" "$LOCAL_RDB" "${VPS_HOST}:${REMOTE_RDB}"
ssh "$VPS_HOST" "ls -la '${REMOTE_RDB}' && file '${REMOTE_RDB}'"

cat <<EOF
[migrate] DONE
Next on VPS (review first — this replaces Redis data):
  # Confirm Redis can load this RDB version (Mac=${MAC_REDIS_VER:-unknown} VPS=${VPS_REDIS_VER:-unknown})
  sudo systemctl stop redis-server
  sudo cp ${REMOTE_RDB} /var/lib/redis/dump.rdb
  sudo chown redis:redis /var/lib/redis/dump.rdb
  sudo systemctl start redis-server
  sudo systemctl status redis-server --no-pager
EOF
