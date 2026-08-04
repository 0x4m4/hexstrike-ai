#!/usr/bin/env bash
# bootstrap-new-vps-onbox.sh — run AS ROOT on the VPS (web/VNC console).
#
# Use when cloud agents / remote SSH get: Connection reset during KEX.
# Paste into MiroHost (or hoster) console after first password login.
#
#   curl -fsSL https://raw.githubusercontent.com/Banda198565/hexstrike-ai/master/scripts/bootstrap-new-vps-onbox.sh | bash
#
# Or from a checked-out tree:
#   bash scripts/bootstrap-new-vps-onbox.sh
#
# Env (optional):
#   REPO_URL=... REMOTE_DIR=/root/hexstrike-ai
#   KEEP_PASSWORD_AUTH=1          # default 1 on first bootstrap
#   SKIP_OSINT=1
#   SHODAN_API_KEY=... ARKHAM_API_KEY=... FOFA_API_KEY=...  # written into .env
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Banda198565/hexstrike-ai.git}"
REMOTE_DIR="${REMOTE_DIR:-/root/hexstrike-ai}"
BRANCH="${BOOTSTRAP_BRANCH:-master}"
KEEP_PASSWORD_AUTH="${KEEP_PASSWORD_AUTH:-1}"
SKIP_OSINT="${SKIP_OSINT:-0}"

log() { echo "[vps-onbox] $*"; }
die() { echo "[vps-onbox] ERROR: $*" >&2; exit 1; }

[[ $(id -u) -eq 0 ]] || die "Run as root (VNC/console)"

export DEBIAN_FRONTEND=noninteractive
log "1/6 apt update + base packages"
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl ca-certificates openssh-server

log "2/6 clone/update repo → $REMOTE_DIR ($BRANCH)"
if [[ -d "$REMOTE_DIR/.git" ]]; then
  git -C "$REMOTE_DIR" fetch origin
  git -C "$REMOTE_DIR" checkout "$BRANCH"
  git -C "$REMOTE_DIR" pull --ff-only origin "$BRANCH" || true
else
  rm -rf "$REMOTE_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$REMOTE_DIR"
fi
cd "$REMOTE_DIR"

log "3/6 python venv + requirements"
python3 -m venv hexstrike-env
# shellcheck disable=SC1091
source hexstrike-env/bin/activate
pip install -q --upgrade pip
if [[ -f requirements-samson.txt ]]; then
  pip install -q -r requirements-samson.txt
elif [[ -f requirements.txt ]]; then
  pip install -q -r requirements.txt
fi

log "4/6 SSH harden (KEEP_PASSWORD_AUTH=$KEEP_PASSWORD_AUTH, no forced passwd rotate)"
KEEP_PASSWORD_AUTH="$KEEP_PASSWORD_AUTH" bash scripts/vps-ssh-harden.sh

log "5/6 .env"
if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
fi
_upsert() {
  local k="$1" v="$2"
  [[ -n "$v" ]] || return 0
  if grep -qE "^${k}=" .env 2>/dev/null; then
    sed -i "s|^${k}=.*|${k}=${v}|" .env
  else
    echo "${k}=${v}" >>.env
  fi
}
# Mirror common aliases from process env (never echo values)
_upsert SHODAN_API_KEY "${SHODAN_API_KEY:-}"
_upsert SAMSON_SHODAN_API_KEY "${SAMSON_SHODAN_API_KEY:-${SHODAN_API_KEY:-}}"
_upsert ARKHAM_API_KEY "${ARKHAM_API_KEY:-${SAMSON_ARKHAM_API_KEY:-}}"
_upsert SAMSON_ARKHAM_API_KEY "${SAMSON_ARKHAM_API_KEY:-${ARKHAM_API_KEY:-}}"
_upsert FOFA_API_KEY "${FOFA_API_KEY:-${SAMSON_FOFA_API_KEY:-}}"
_upsert SAMSON_FOFA_API_KEY "${SAMSON_FOFA_API_KEY:-${FOFA_API_KEY:-}}"
_upsert COINSTATS_API_KEY "${COINSTATS_API_KEY:-${SAMSON_COINSTATS_API_KEY:-}}"
_upsert SAMSON_COINSTATS_API_KEY "${SAMSON_COINSTATS_API_KEY:-${COINSTATS_API_KEY:-}}"
_upsert GETBLOCK_API_KEY "${GETBLOCK_API_KEY:-}"
_upsert GITHUB_TOKEN "${GITHUB_TOKEN:-}"
_upsert ETHERSCAN_API_KEY "${ETHERSCAN_API_KEY:-${BSCSCAN_API_KEY:-}}"
_upsert BSCSCAN_API_KEY "${BSCSCAN_API_KEY:-${ETHERSCAN_API_KEY:-}}"
chmod 600 .env
# Count nonempty secret keys without printing
python3 - <<'PY'
from pathlib import Path
keys = []
for line in Path(".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        if v.strip() and "change-me" not in v:
            keys.append(k.strip())
need = {"SHODAN_API_KEY","ARKHAM_API_KEY","SAMSON_ARKHAM_API_KEY","FOFA_API_KEY"}
have = set(keys) & need
print(f"[vps-onbox] .env nonempty keys={len(keys)} osint_core={sorted(have)}")
if len(have) < 2:
    print("[vps-onbox] WARN: export SHODAN_API_KEY / ARKHAM_API_KEY then re-run, or scp .env from Mac")
PY

log "6/6 health + optional OSINT smoke"
mkdir -p artifacts docs/recon
python3 - <<PY
import json, platform, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
status = {
  "generated_at": datetime.now(timezone.utc).isoformat(),
  "host": platform.node(),
  "remote_dir": "$REMOTE_DIR",
  "branch": "$BRANCH",
  "python": shutil.which("python3"),
  "git": subprocess.check_output(["git","rev-parse","--short","HEAD"], text=True).strip(),
  "keep_password_auth": "$KEEP_PASSWORD_AUTH" == "1",
  "env_present": Path(".env").is_file(),
  "mode": "lab_defense_bootstrap",
}
Path("artifacts/vps-bootstrap-status.json").write_text(json.dumps(status, indent=2) + "\n")
print(json.dumps(status, indent=2))
PY

if [[ "$SKIP_OSINT" != "1" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  export PYTHONPATH="$REMOTE_DIR:$REMOTE_DIR/src:${PYTHONPATH:-}"
  if [[ -n "${SHODAN_API_KEY:-}" ]]; then
    bash scripts/run-ru-shodan-recon.sh || log "WARN: RU shodan smoke failed"
    bash scripts/run-kz-shodan-recon.sh || log "WARN: KZ shodan smoke failed"
  else
    log "SKIP shodan smoke — SHODAN_API_KEY empty"
  fi
  if [[ -n "${ARKHAM_API_KEY:-${SAMSON_ARKHAM_API_KEY:-}}" ]]; then
    export ARKHAM_API_KEY="${ARKHAM_API_KEY:-$SAMSON_ARKHAM_API_KEY}"
    bash scripts/arkham-probe.sh || log "WARN: arkham probe failed (Cloudflare possible)"
  else
    log "SKIP arkham smoke — ARKHAM key empty"
  fi
fi

cat <<EOF

[vps-onbox] DONE
  Repo:   $REMOTE_DIR
  Status: $REMOTE_DIR/artifacts/vps-bootstrap-status.json
  Login:  password still enabled (KEEP_PASSWORD_AUTH=$KEEP_PASSWORD_AUTH)
  Next on Mac:
    ssh-copy-id -i ~/.ssh/hexstrike_vps.pub root@YOUR_IP
    scp ~/.env-or-local/.env root@YOUR_IP:$REMOTE_DIR/.env
    # later harden: KEEP_PASSWORD_AUTH=0 bash scripts/vps-ssh-harden.sh

EOF
