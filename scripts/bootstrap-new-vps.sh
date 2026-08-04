#!/usr/bin/env bash
# bootstrap-new-vps.sh — first-time HexStrike VPS setup from YOUR Mac/iMac.
#
# Preferred: key-only (no password):
#   bash scripts/bootstrap-new-vps.sh root@78.27.235.70
#   # uses ~/.ssh/hexstrike_vps or HEXSTRIKE_VPS_KEY / ssh-agent
#
# Password fallback (only if key login fails):
#   read -s VPS_PASSWORD; export VPS_PASSWORD; echo
#   bash scripts/bootstrap-new-vps.sh root@HOST
#
# Console fallback (SSH KEX reset from cloud/Mac):
#   curl -fsSL https://raw.githubusercontent.com/Banda198565/hexstrike-ai/master/scripts/bootstrap-new-vps-onbox.sh | bash
#
# Defaults:
#   SKIP_PASSWD_ROTATE=1  KEEP_PASSWORD_AUTH=1  SKIP_OSINT=0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-}"
KEY="${HEXSTRIKE_VPS_KEY:-$HOME/.ssh/hexstrike_vps}"
LOCAL_ENV="${LOCAL_ENV:-$ROOT/.env}"
REPO_URL="${REPO_URL:-https://github.com/Banda198565/hexstrike-ai.git}"
REMOTE_DIR="${REMOTE_DIR:-/root/hexstrike-ai}"
BRANCH="${BOOTSTRAP_BRANCH:-master}"

SKIP_PASSWD_ROTATE="${SKIP_PASSWD_ROTATE:-1}"
KEEP_PASSWORD_AUTH="${KEEP_PASSWORD_AUTH:-1}"
SKIP_OSINT="${SKIP_OSINT:-0}"

log() { echo "[bootstrap-vps] $*"; }
die() { echo "[bootstrap-vps] ERROR: $*" >&2; exit 1; }

[[ -n "$TARGET" ]] || die "usage: bash scripts/bootstrap-new-vps.sh root@HOST"
[[ "$TARGET" == *@* ]] || die "TARGET must look like root@IP"
command -v ssh >/dev/null || die "ssh required"

SSH_BASE=(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=25 -o ServerAliveInterval=5)
AUTH_MODE=""

# Resolve SSH helpers: key-first, password optional
ssh_remote() {
  if [[ "$AUTH_MODE" == "key" ]]; then
    ssh -i "$KEY" -o IdentitiesOnly=yes "${SSH_BASE[@]}" "$TARGET" "$@"
  elif [[ "$AUTH_MODE" == "agent" ]]; then
    ssh -o BatchMode=yes "${SSH_BASE[@]}" "$TARGET" "$@"
  else
    sshpass -e "${SSH_BASE[@]}" -o PreferredAuthentications=password -o PubkeyAuthentication=no "$TARGET" "$@"
  fi
}

scp_to() {
  local src="$1" dst="$2"
  if [[ "$AUTH_MODE" == "key" ]]; then
    scp -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new "$src" "$TARGET:$dst"
  elif [[ "$AUTH_MODE" == "agent" ]]; then
    scp -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$src" "$TARGET:$dst"
  else
    sshpass -e scp -o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password -o PubkeyAuthentication=no "$src" "$TARGET:$dst"
  fi
}

# ── Step 1: connect (key → agent → password) ────────────────────
log "Step 1/7: connect → $TARGET (prefer key, no password)"

if [[ -f "$KEY" ]]; then
  if ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes "${SSH_BASE[@]}" "$TARGET" 'echo KEY_OK' 2>/dev/null; then
    AUTH_MODE=key
    log "auth=key ($KEY)"
  fi
fi

if [[ -z "$AUTH_MODE" ]]; then
  if ssh -o BatchMode=yes "${SSH_BASE[@]}" "$TARGET" 'echo AGENT_OK' 2>/dev/null; then
    AUTH_MODE=agent
    log "auth=ssh-agent"
  fi
fi

if [[ -z "$AUTH_MODE" ]]; then
  if [[ -n "${VPS_PASSWORD:-}" ]]; then
    command -v sshpass >/dev/null || die "sshpass required for password auth"
    export SSHPASS="$VPS_PASSWORD"
    if sshpass -e "${SSH_BASE[@]}" -o PreferredAuthentications=password -o PubkeyAuthentication=no "$TARGET" 'echo PASS_OK'; then
      AUTH_MODE=password
      log "auth=password"
    fi
  fi
fi

if [[ -z "$AUTH_MODE" ]]; then
  cat <<EOF >&2

[bootstrap-vps] Cannot SSH to $TARGET (key/agent/password all failed).

If you see "Connection reset" during KEX — your IP or Cursor cloud IP is blocked
before auth. Fix via hoster VNC/console:

  curl -fsSL https://raw.githubusercontent.com/Banda198565/hexstrike-ai/master/scripts/bootstrap-new-vps-onbox.sh | bash

Whitelist Cursor cloud egress if you want agents to SSH later:
  54.201.20.43
  52.13.17.46

Or from Mac (where key works):
  bash scripts/bootstrap-new-vps.sh $TARGET

EOF
  die "SSH connect failed"
fi

ssh_remote 'echo LOGIN_OK; uname -a; whoami'

# ── Step 2: optional password rotate (OFF by default) ───────────
if [[ "$SKIP_PASSWD_ROTATE" == "1" ]]; then
  log "Step 2/7: SKIP password rotate"
elif [[ "$AUTH_MODE" == "password" ]]; then
  NEW_PASS="$(python3 -c 'import secrets,string; a=string.ascii_letters+string.digits; print("".join(secrets.choice(a) for _ in range(28)))')"
  log "Step 2/7: rotating root password"
  ssh_remote "echo 'root:${NEW_PASS}' | chpasswd && echo PASSWD_OK"
  echo; echo "========== NEW ROOT PASSWORD =========="; echo "$NEW_PASS"; echo "======================================"; echo
  export SSHPASS="$NEW_PASS"
else
  log "Step 2/7: SKIP rotate (not using password auth session)"
fi

# ── Step 3: ensure our key is installed (idempotent) ────────────
log "Step 3/7: ensure ed25519 pubkey on VPS"
if [[ ! -f "$KEY" ]]; then
  ssh-keygen -t ed25519 -f "$KEY" -N "" -C "hexstrike-vps-$(whoami)@$(hostname)-$(date +%Y%m%d)"
fi
chmod 600 "$KEY" "${KEY}.pub" 2>/dev/null || chmod 600 "$KEY"
PUB="$(cat "${KEY}.pub")"
ssh_remote "bash -s" <<EOF
set -euo pipefail
mkdir -p /root/.ssh && chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys
grep -qxF '$PUB' /root/.ssh/authorized_keys || echo '$PUB' >> /root/.ssh/authorized_keys
echo KEY_INSTALLED
EOF
# Prefer key for remainder
if ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes "${SSH_BASE[@]}" "$TARGET" 'echo KEY_LOGIN_OK' 2>/dev/null; then
  AUTH_MODE=key
fi

# ── Step 4: onbox bootstrap remotely ────────────────────────────
log "Step 4/7: remote onbox (apt/clone/venv/harden)"
scp_to "$ROOT/scripts/bootstrap-new-vps-onbox.sh" "/tmp/bootstrap-new-vps-onbox.sh"
ssh_remote "KEEP_PASSWORD_AUTH=$KEEP_PASSWORD_AUTH SKIP_OSINT=1 REPO_URL='$REPO_URL' REMOTE_DIR='$REMOTE_DIR' BOOTSTRAP_BRANCH='$BRANCH' bash /tmp/bootstrap-new-vps-onbox.sh"

# ── Step 5: .env ────────────────────────────────────────────────
log "Step 5/7: sync .env"
if [[ -f "$LOCAL_ENV" ]]; then
  scp_to "$LOCAL_ENV" "$REMOTE_DIR/.env"
  ssh_remote "chmod 600 '$REMOTE_DIR/.env' && echo ENV_SYNC_OK"
else
  log "WARN: $LOCAL_ENV missing"
fi

# ── Step 6: OSINT ───────────────────────────────────────────────
if [[ "$SKIP_OSINT" != "1" ]]; then
  log "Step 6/7: OSINT smoke"
  ssh_remote "bash -s" <<EOF
set -euo pipefail
cd '$REMOTE_DIR'
set -a
# shellcheck disable=SC1091
[[ -f .env ]] && source .env
set +a
# shellcheck disable=SC1091
source hexstrike-env/bin/activate
export PYTHONPATH='$REMOTE_DIR:$REMOTE_DIR/src:\${PYTHONPATH:-}'
export ARKHAM_API_KEY="\${ARKHAM_API_KEY:-\${SAMSON_ARKHAM_API_KEY:-}}"
mkdir -p artifacts docs/recon
[[ -n "\${SHODAN_API_KEY:-}" ]] && bash scripts/run-ru-shodan-recon.sh || true
[[ -n "\${SHODAN_API_KEY:-}" ]] && bash scripts/run-kz-shodan-recon.sh || true
[[ -n "\${ARKHAM_API_KEY:-}" ]] && bash scripts/arkham-probe.sh || true
echo OSINT_SMOKE_DONE
EOF
else
  log "Step 6/7: SKIP OSINT"
fi

# ── Step 7: verify ──────────────────────────────────────────────
log "Step 7/7: verify"
ssh_remote "bash -s" <<EOF
set -euo pipefail
cd '$REMOTE_DIR'
test -d hexstrike-env
test -f artifacts/vps-bootstrap-status.json && cat artifacts/vps-bootstrap-status.json || true
# shellcheck disable=SC1091
source hexstrike-env/bin/activate
python3 -c 'import sys; print("python", sys.version.split()[0])'
echo VERIFY_OK
EOF

cat <<EOF

[bootstrap-vps] DONE
  ssh -i $KEY $TARGET
  auth_mode=$AUTH_MODE skip_passwd=$SKIP_PASSWD_ROTATE keep_password_auth=$KEEP_PASSWORD_AUTH

EOF
