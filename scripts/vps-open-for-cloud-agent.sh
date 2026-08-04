#!/usr/bin/env bash
# ONE shot from YOUR Mac (where key SSH already works).
# 1) allowlists Cursor cloud egress IPs
# 2) installs cloud-agent pubkey
# 3) runs onbox bootstrap (no password rotate)
# 4) syncs local .env if present
#
#   cd ~/hexstrike-ai && git pull
#   bash scripts/vps-open-for-cloud-agent.sh root@78.27.235.70
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-root@78.27.235.70}"
KEY="${HEXSTRIKE_VPS_KEY:-$HOME/.ssh/hexstrike_vps}"
LOCAL_ENV="${LOCAL_ENV:-$ROOT/.env}"
REMOTE_DIR="${REMOTE_DIR:-/root/hexstrike-ai}"

# Current Cursor cloud egress (update if agent IP changes)
CLOUD_IPS=("52.40.48.127" "44.236.205.197" "52.13.17.46" "54.201.20.43")
# Pubkey from cloud agent session (hexstrike_vps generated 2026-07-17)
CLOUD_PUB='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG3ASf+3bbpvVwpI2zdjpRz2HmayHivj8++CbV7eGIYg hexstrike-cloud-agent-20260717'

log() { echo "[open-cloud] $*"; }
die() { echo "[open-cloud] ERROR: $*" >&2; exit 1; }

SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
SCP=(scp -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
if [[ -f "$KEY" ]]; then
  SSH=(ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
  SCP=(scp -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
fi

log "test login $TARGET"
"${SSH[@]}" "$TARGET" 'echo OPERATOR_KEY_OK; whoami' || die "Your Mac cannot SSH either — fix key first"

log "allowlist cloud IPs + install cloud agent pubkey"
IPS_CSV="$(IFS=,; echo "${CLOUD_IPS[*]}")"
"${SSH[@]}" "$TARGET" "bash -s" <<EOF
set -euo pipefail
IPS=($IPS_CSV)
PUB='$CLOUD_PUB'
mkdir -p /root/.ssh && chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys
grep -qxF "\$PUB" /root/.ssh/authorized_keys || echo "\$PUB" >> /root/.ssh/authorized_keys
for ip in "\${IPS[@]}"; do
  if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -qi active; then
    ufw allow from "\$ip" to any port 22 proto tcp comment cursor-cloud || true
  fi
  if command -v fail2ban-client >/dev/null 2>&1; then
    fail2ban-client set sshd unbanip "\$ip" 2>/dev/null || true
    fail2ban-client set ssh unbanip "\$ip" 2>/dev/null || true
  fi
  if command -v iptables >/dev/null 2>&1; then
    iptables -C INPUT -p tcp -s "\$ip" --dport 22 -j ACCEPT 2>/dev/null \\
      || iptables -I INPUT 1 -p tcp -s "\$ip" --dport 22 -j ACCEPT
  fi
  # firewalld
  if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state 2>/dev/null | grep -q running; then
    firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=\${ip}/32 port port=22 protocol=tcp accept" || true
    firewall-cmd --reload || true
  fi
  echo "allowed \$ip"
done
# If hosts.deny blocks ALL, soften
if [[ -f /etc/hosts.deny ]] && grep -qiE '^sshd\\s*:\\s*ALL' /etc/hosts.deny; then
  for ip in "\${IPS[@]}"; do
    grep -q "sshd: \$ip" /etc/hosts.allow 2>/dev/null || echo "sshd: \$ip  # cursor-cloud" >> /etc/hosts.allow
  done
fi
echo ALLOW_DONE
EOF

log "upload + run onbox bootstrap"
"${SCP[@]}" "$ROOT/scripts/bootstrap-new-vps-onbox.sh" "$TARGET:/tmp/bootstrap-new-vps-onbox.sh"
"${SSH[@]}" "$TARGET" 'KEEP_PASSWORD_AUTH=1 SKIP_OSINT=1 bash /tmp/bootstrap-new-vps-onbox.sh'

if [[ -f "$LOCAL_ENV" ]]; then
  log "sync .env"
  "${SCP[@]}" "$LOCAL_ENV" "$TARGET:$REMOTE_DIR/.env"
  "${SSH[@]}" "$TARGET" "chmod 600 $REMOTE_DIR/.env"
fi

log "OSINT smoke"
"${SSH[@]}" "$TARGET" "bash -s" <<EOF
set -euo pipefail
cd $REMOTE_DIR
set -a; source .env 2>/dev/null || true; set +a
source hexstrike-env/bin/activate
export PYTHONPATH=$REMOTE_DIR:$REMOTE_DIR/src
export ARKHAM_API_KEY="\${ARKHAM_API_KEY:-\${SAMSON_ARKHAM_API_KEY:-}}"
mkdir -p artifacts docs/recon
[[ -n "\${SHODAN_API_KEY:-}" ]] && bash scripts/run-ru-shodan-recon.sh || true
[[ -n "\${SHODAN_API_KEY:-}" ]] && bash scripts/run-kz-shodan-recon.sh || true
[[ -n "\${ARKHAM_API_KEY:-}" ]] && bash scripts/arkham-probe.sh || true
cat artifacts/vps-bootstrap-status.json 2>/dev/null || true
echo ALL_DONE
EOF

cat <<EOF

[open-cloud] DONE on VPS.
Cloud agent can now retry SSH from: ${CLOUD_IPS[*]}
Reply to the agent: retry

EOF
