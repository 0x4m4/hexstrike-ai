#!/usr/bin/env bash
# Harden root SSH on HexStrike VPS: install agent pubkey, disable password auth.
#
# Run as root on the VPS (MiroHost web/VNC console if SSH is locked out):
#   curl -fsSL https://raw.githubusercontent.com/banda198565/hexstrike-ai/master/scripts/vps-ssh-harden.sh | bash
#
# Optional:
#   NEW_ROOT_PASSWORD='...' bash scripts/vps-ssh-harden.sh   # rotate root password
#   KEEP_PASSWORD_AUTH=1 bash scripts/vps-ssh-harden.sh      # install key only, keep password login
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Canonical key file when present; embedded fallbacks for curl|bash installs.
PUBKEY_FILE="${HEXSTRIKE_VPS_PUBKEY_FILE:-$SCRIPT_DIR/hexstrike_vps_key.pub}"
PUBKEY_PRIMARY_FALLBACK="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOc4+341bbWPywULPF8MTDq9VpaDMT4+TqKLpK4Uo2Gs hexstrike-01@cursor-20260714"
PUBKEY_LEGACY_FALLBACK="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIByufH4aDtJgrm/Udc3Vai4heLmGhT2N4xKdZ5bjZ0DH cursor-cloud-hexstrike"

SSHD_CFG="/etc/ssh/sshd_config"
SSHD_DROPIN_DIR="/etc/ssh/sshd_config.d"
# Ubuntu: sshd uses FIRST obtained value; Include loads sshd_config.d before the rest
# of sshd_config, so cloud-init's PasswordAuthentication yes wins unless overridden
# in an early drop-in (00-*) and/or by patching 50-cloud-init.conf in place.
DROPIN_FIRST="${SSHD_DROPIN_DIR}/00-hexstrike-harden.conf"
DROPIN_LAST="${SSHD_DROPIN_DIR}/99-hexstrike-harden.conf"

log() { echo "[vps-ssh-harden] $*"; }
die() { echo "[vps-ssh-harden] ERROR: $*" >&2; exit 1; }

[[ $(id -u) -eq 0 ]] || die "Run as root (MiroHost console / sudo)"

load_pubkeys() {
  PUBKEYS=()
  if [[ -f "$PUBKEY_FILE" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "${line// }" || "$line" =~ ^# ]] && continue
      PUBKEYS+=("$line")
    done <"$PUBKEY_FILE"
    log "loaded ${#PUBKEYS[@]} key(s) from $PUBKEY_FILE"
  fi
  if [[ ${#PUBKEYS[@]} -eq 0 ]]; then
    log "pubkey file missing/empty ($PUBKEY_FILE) — using embedded fallbacks (curl|bash mode)"
    PUBKEYS=("$PUBKEY_PRIMARY_FALLBACK" "$PUBKEY_LEGACY_FALLBACK")
  elif [[ ${#PUBKEYS[@]} -eq 1 ]]; then
    # Keep legacy recovery key alongside canonical file key
    PUBKEYS+=("$PUBKEY_LEGACY_FALLBACK")
  fi
}

mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

install_key() {
  local key="$1"
  local comment
  comment="$(awk '{print $NF}' <<<"$key")"
  if grep -qF "$key" /root/.ssh/authorized_keys 2>/dev/null; then
    log "key already present: $comment"
  else
    echo "$key" >> /root/.ssh/authorized_keys
    log "installed key: $comment"
  fi
}

load_pubkeys
for key in "${PUBKEYS[@]}"; do
  install_key "$key"
done

PRIMARY_KEY="${PUBKEYS[0]}"
PRIMARY_COMMENT="$(awk '{print $NF}' <<<"$PRIMARY_KEY")"

if [[ -n "${NEW_ROOT_PASSWORD:-}" ]]; then
  log "rotating root password from NEW_ROOT_PASSWORD"
  echo "root:${NEW_ROOT_PASSWORD}" | chpasswd
else
  log "NEW_ROOT_PASSWORD unset — root password left unchanged"
fi

mkdir -p "$SSHD_DROPIN_DIR"

write_harden_dropins() {
  local password_auth="$1"
  local permit_root="$2"
  local body
  body=$(cat <<EOF
# HexStrike SSH harden
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PermitRootLogin ${permit_root}
PasswordAuthentication ${password_auth}
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
EOF
)
  printf '%s\n' "$body" >"$DROPIN_FIRST"
  printf '%s\n' "$body" >"$DROPIN_LAST"
}

# Patch PasswordAuthentication in place — do not wipe other cloud-init directives.
patch_password_auth_no() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  if grep -qE '^[[:space:]]*PasswordAuthentication[[:space:]]+' "$f"; then
    sed -i -E 's/^[[:space:]]*PasswordAuthentication.*/PasswordAuthentication no/' "$f"
    log "patched $f PasswordAuthentication -> no (other directives preserved)"
  elif grep -qE 'PasswordAuthentication[[:space:]]+yes' "$f"; then
    sed -i -E 's/^([#[:space:]]*)PasswordAuthentication.*/PasswordAuthentication no/' "$f"
    log "patched commented/alternate PasswordAuthentication in $f"
  fi
}

if [[ "${KEEP_PASSWORD_AUTH:-0}" == "1" ]]; then
  write_harden_dropins yes yes
  log "KEEP_PASSWORD_AUTH=1 — password login still enabled"
else
  write_harden_dropins no prohibit-password
  for f in "${SSHD_DROPIN_DIR}/50-cloud-init.conf" "${SSHD_DROPIN_DIR}/60-cloudimg-settings.conf"; do
    patch_password_auth_no "$f"
  done
  if grep -qE '^[#[:space:]]*PasswordAuthentication[[:space:]]+' "$SSHD_CFG" 2>/dev/null; then
    sed -i -E 's/^[#[:space:]]*PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CFG"
  fi
  if grep -qE '^[#[:space:]]*PermitRootLogin[[:space:]]+' "$SSHD_CFG" 2>/dev/null; then
    sed -i -E 's/^[#[:space:]]*PermitRootLogin.*/PermitRootLogin prohibit-password/' "$SSHD_CFG"
  fi
  sed -i '/# HEXSTRIKE_HARDEN_BEGIN/,/# HEXSTRIKE_HARDEN_END/d' "$SSHD_CFG"
  cat >>"$SSHD_CFG" <<'EOF'

# HEXSTRIKE_HARDEN_BEGIN
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
# HEXSTRIKE_HARDEN_END
EOF
  log "password authentication disabled (key-only)"
fi

sshd -t || die "sshd_config validation failed — not restarting ssh"

if systemctl is-active --quiet ssh 2>/dev/null; then
  systemctl reload ssh || systemctl restart ssh
elif systemctl is-active --quiet sshd 2>/dev/null; then
  systemctl reload sshd || systemctl restart sshd
else
  service ssh reload 2>/dev/null || service ssh restart 2>/dev/null || \
    service sshd reload 2>/dev/null || service sshd restart 2>/dev/null || \
    die "could not reload ssh/sshd"
fi

eff_pass="$(sshd -T 2>/dev/null | awk '/^passwordauthentication /{print $2}')"
eff_root="$(sshd -T 2>/dev/null | awk '/^permitrootlogin /{print $2}')"
eff_pubkey="$(sshd -T 2>/dev/null | awk '/^pubkeyauthentication /{print $2}')"
eff_authkeys="$(sshd -T 2>/dev/null | awk '/^authorizedkeysfile /{print $2}')"
log "sshd reloaded (passwordauthentication=${eff_pass:-unknown} permitrootlogin=${eff_root:-unknown} pubkeyauthentication=${eff_pubkey:-unknown})"

# Fail-closed verification — avoid lockout after disabling passwords.
if [[ "${eff_pubkey:-}" != "yes" ]]; then
  die "effective PubkeyAuthentication is '${eff_pubkey:-unset}', expected yes — aborting to avoid lockout"
fi
if ! grep -qF "$PRIMARY_KEY" /root/.ssh/authorized_keys 2>/dev/null; then
  die "primary pubkey missing from /root/.ssh/authorized_keys — aborting"
fi
case "${eff_root:-}" in
  prohibit-password|without-password|yes|forced-commands-only) ;;
  *)
    die "effective PermitRootLogin is '${eff_root:-unset}', expected prohibit-password|without-password|yes"
    ;;
esac
if [[ "${KEEP_PASSWORD_AUTH:-0}" != "1" && "${eff_pass:-}" != "no" ]]; then
  die "effective PasswordAuthentication is '${eff_pass:-unset}', expected no"
fi

log "authorized_keys entries: $(wc -l </root/.ssh/authorized_keys) (primary=${PRIMARY_COMMENT})"
log "AuthorizedKeysFile effective: ${eff_authkeys:-.ssh/authorized_keys}"
log "DONE — verify from a second session BEFORE closing console: ssh -i <key> root@<host>"
echo "fingerprint expected: SHA256:78K9fBhhOGmuThLoir5QsfVIn3nL970N1/q/aPN5eyQ"
