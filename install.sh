#!/usr/bin/env bash
#
# install.sh — HexStrike AI v6.0.1 fixed installer (fork: ZanderoDev/hexstrike-ai-update)
#
# Fixes vs old manual README install:
#   1. No installer existed at all — this is the new single entry point.
#   2. requirements.txt pinned broken `fastmcp` + forced heavy builds
#      (pwntools/angr/mitmproxy/selenium) -> now core-only by default,
#      extras opt-in via --with-* flags. Python 3.10-3.12 enforced.
#   3. /health tool detection used `execute_command("which ...")` (100+
#      slow shell subprocesses, cache only hits, duplicate tool names,
#      wrong binary names, missing ~/go/bin PATH) -> server now uses
#      shutil.which+importlib alias-aware detection; installer mirrors it
#      with fast `command -v` scans and installs ONLY missing tools.
#   4. MCP client used 5s /health timeout + 3x2s blocking retries at
#      startup -> MCP hosts killed it ("Connection closed"). Now
#      --health-timeout 15 + --lazy + compat FastMCP import; installer
#      writes a working opencode.json automatically.
#
# Usage:
#   ./install.sh [options]
#   ./install.sh --categories "network web" --yes
#   ./install.sh --with-all --with-opencode --check-health
#
# Options:
#   --categories "net web ..."  use-case set (default: interactive ask)
#     valid: network web exploit password osint wireless forensics cloud all
#   --yes, -y                   non-interactive (assume yes)
#   --with-browser              also pip-install selenium extras
#   --with-proxy                also pip-install mitmproxy extras
#   --with-pwn                  also pip-install pwntools+angr extras (needs py3.11/3.12)
#   --with-all                  all three extras above
#   --with-opencode             also install OpenCode via npm (needs node/npm)
#   --check-health              start server, curl /health, show coverage, stop server
#   --port PORT                 server port for config/health (default 8888)
#   --no-tools                  skip security-tool installs (python env + MCP config only)
#   -h, --help                  this help
#
# Safe to re-run. Run as normal user (not via sudo); sudo is used internally.

set -uo pipefail

# ---------------------------------------------------------------- presentation
if [[ -t 1 ]]; then
  BOLD="$(tput bold)"; RESET="$(tput sgr0)"
  RED="$(tput setaf 1)"; GREEN="$(tput setaf 2)"
  YELLOW="$(tput setaf 3)"; BLUE="$(tput setaf 4)"; CYAN="$(tput setaf 6)"
else
  BOLD=""; RESET=""; RED=""; GREEN=""; YELLOW=""; BLUE=""; CYAN=""
fi
info()    { echo "${BLUE}[*]${RESET} $*"; }
success() { echo "${GREEN}[✓]${RESET} $*"; }
warn()    { echo "${YELLOW}[!]${RESET} $*" >&2; }
err()     { echo "${RED}[✗]${RESET} $*" >&2; }
step()    { echo; echo "${BOLD}${CYAN}==> $*${RESET}"; }
die()     { err "$*"; exit 1; }

# ---------------------------------------------------------------- globals
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEXSTRIKE_DIR="$SCRIPT_DIR"
VENV_DIR="${HEXSTRIKE_DIR}/hexstrike-env"
VENV_PY="${VENV_DIR}/bin/python"
VENV_PIP="${VENV_DIR}/bin/pip"
OC_CONFIG_DIR="${HOME}/.config/opencode"
OC_CONFIG="${OC_CONFIG_DIR}/opencode.json"
SERVER_PORT="8888"
GO_VERSION="1.23.4"
YES=0; NO_TOOLS=0; CHECK_HEALTH=0; WITH_OPENCODE=0
WITH_BROWSER=0; WITH_PROXY=0; WITH_PWN=0
CATEGORIES_ARG=""
ALL_CATS="network web exploit password osint wireless forensics cloud"
declare -a SELECTED_CATS=()

export PATH="/usr/local/go/bin:${HOME}/go/bin:${HOME}/.cargo/bin:${HOME}/.local/bin:${PATH}"

usage() { sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; }

# ---------------------------------------------------------------- args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --categories) CATEGORIES_ARG="${2:-}"; shift 2 ;;
    --yes|-y) YES=1; shift ;;
    --with-browser) WITH_BROWSER=1; shift ;;
    --with-proxy) WITH_PROXY=1; shift ;;
    --with-pwn) WITH_PWN=1; shift ;;
    --with-all) WITH_BROWSER=1; WITH_PROXY=1; WITH_PWN=1; shift ;;
    --with-opencode) WITH_OPENCODE=1; shift ;;
    --check-health) CHECK_HEALTH=1; shift ;;
    --port) SERVER_PORT="${2:-8888}"; shift 2 ;;
    --no-tools) NO_TOOLS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1 (see --help)" ;;
  esac
done

confirm() {
  [[ $YES -eq 1 ]] && return 0
  local prompt="${1:-Continue?}" answer
  read -r -p "${prompt} [Y/n] " answer
  answer="${answer:-Y}"; [[ "$answer" =~ ^[Yy]$ ]]
}

have() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- 1. distro + python
step "1/7 — Checking system prerequisites"

DISTRO="unknown"
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  case "${ID:-}" in
    kali) DISTRO="kali" ;;
    ubuntu) DISTRO="ubuntu" ;;
    debian) DISTRO="debian" ;;
    *) DISTRO="${ID:-unknown}" ;;
  esac
fi
info "Distro: ${DISTRO} | User: $(whoami) | Repo: ${HEXSTRIKE_DIR}"

have python3 || die "python3 not found. Install it first (sudo apt install python3 python3-venv python3-pip)."
PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
info "Python: $(python3 --version 2>&1)"
if [[ "$PY_MAJOR" -ne 3 || "$PY_MINOR" -lt 10 ]]; then
  die "Python >=3.10 required (found ${PY_VER})."
fi
if [[ "$PY_MINOR" -ge 13 ]]; then
  warn "Python ${PY_VER} detected: pwntools/angr/mitmproxy often FAIL to build here."
  warn "Core install will work; extras (--with-pwn/--with-proxy) need Python 3.11/3.12."
  confirm "Continue anyway with core-only install?" || exit 1
fi
if [[ $WITH_PWN -eq 1 && "$PY_MINOR" -ge 13 ]]; then
  warn "--with-pwn on Python 3.13+ will very likely fail. Continuing anyway..."
fi

info "Installing base packages (git, venv, curl, build tools, jq)..."
sudo apt-get update -qq 2>&1 | tail -n 2 || warn "apt-get update had warnings (continuing)."
sudo apt-get install -y -qq git python3-venv python3-pip python3-dev curl wget jq \
  build-essential pkg-config libssl-dev libffi-dev tmux 2>&1 | tail -n 3 \
  || die "Failed to install base packages."

# ---------------------------------------------------------------- 2. tool catalogue
# category_tools <cat> echoes "binary|method|target" lines.
# method: apt | pipx | go | cargo | gem | manual
category_tools() {
  case "$1" in
    network)
      cat <<'EOF'
nmap|apt|nmap
masscan|apt|masscan
arp-scan|apt|arp-scan
nbtscan|apt|nbtscan
enum4linux|apt|enum4linux
smbmap|apt|smbmap
responder|apt|responder
rpcclient|apt|smbclient
autorecon|pipx|autorecon
enum4linux-ng|pipx|enum4linux-ng
rustscan|apt|rustscan
EOF
      [[ "$DISTRO" != "kali" ]] && echo "rustscan|cargo|rustscan"
      ;;
    web)
      cat <<'EOF'
gobuster|apt|gobuster
ffuf|apt|ffuf
feroxbuster|apt|feroxbuster
nikto|apt|nikto
sqlmap|apt|sqlmap
wpscan|apt|wpscan
dirb|apt|dirb
dirsearch|apt|dirsearch
wfuzz|apt|wfuzz
dalfox|go|github.com/hahwul/dalfox/v2
httpx|go|github.com/projectdiscovery/httpx/cmd/httpx
katana|go|github.com/projectdiscovery/katana/cmd/katana
nuclei|go|github.com/projectdiscovery/nuclei/v3/cmd/nuclei
subfinder|go|github.com/projectdiscovery/subfinder/v2/cmd/subfinder
arjun|pipx|arjun
paramspider|pipx|paramspider
gau|go|github.com/lc/gau/v2/cmd/gau
waybackurls|go|github.com/tomnomnom/waybackurls
hakrawler|go|github.com/hakluke/hakrawler
qsreplace|go|github.com/tomnomnom/qsreplace
anew|go|github.com/tomnomnom/anew
uro|pipx|uro
wafw00f|pipx|wafw00f
EOF
      ;;
    exploit)
      cat <<'EOF'
msfconsole|apt|metasploit-framework
msfvenom|apt|metasploit-framework
searchsploit|apt|exploitdb
EOF
      ;;
    password)
      cat <<'EOF'
hydra|apt|hydra
john|apt|john
hashcat|apt|hashcat
medusa|apt|medusa
patator|apt|patator
ophcrack|apt|ophcrack
evil-winrm|gem|evil-winrm
hash-identifier|apt|hash-identifier
EOF
      ;;
    osint)
      cat <<'EOF'
amass|apt|amass
fierce|apt|fierce
dnsenum|apt|dnsenum
theHarvester|pipx|theharvester
sherlock|pipx|sherlock-project
subfinder|go|github.com/projectdiscovery/subfinder/v2/cmd/subfinder
EOF
      ;;
    wireless)
      cat <<'EOF'
kismet|apt|kismet
wireshark|apt|wireshark
tshark|apt|tshark
tcpdump|apt|tcpdump
aircrack-ng|apt|aircrack-ng
EOF
      ;;
    forensics)
      cat <<'EOF'
binwalk|apt|binwalk
foremost|apt|foremost
steghide|apt|steghide
exiftool|apt|libimage-exiftool-perl
volatility3|pipx|volatility3
scalpel|apt|scalpel
zsteg|gem|zsteg
EOF
      ;;
    cloud)
      cat <<'EOF'
trivy|apt|trivy
checkov|pipx|checkov
prowler|pipx|prowler
scout-suite|pipx|scoutsuite
EOF
      ;;
  esac
}

# installed? mirrors server resolve_tool(): binary candidates + common renames
is_installed() {
  local bin="$1"
  case "$bin" in
    theHarvester) have theHarvester || have theharvester ;;
    nxc) have nxc || have crackmapexec || have netexec ;;
    msfconsole|msfvenom|searchsploit) have "$bin" ;;
    vol|volatility3) have vol || have volatility3 || have vol.py ;;
    one_gadget|one-gadget) have one_gadget || have one-gadget ;;
    shodan) have shodan ;;
    hibp) have hibp || have have-i-been-pwned ;;
    *) have "$bin" ;;
  esac
}

# ---------------------------------------------------------------- 3. scan
step "2/7 — Scanning existing tools (fast command -v scan, installs only what's missing)"
declare -A SEEN=()
declare -a MISSING_LINES=()
TOTAL=0; FOUND=0
for cat in $ALL_CATS; do
  avail=0; total=0
  while IFS='|' read -r bin method target; do
    [[ -z "$bin" ]] && continue
    key="${bin}"
    [[ -n "${SEEN[$key]:-}" ]] && continue
    SEEN[$key]=1
    total=$((total+1)); TOTAL=$((TOTAL+1))
    if is_installed "$bin"; then avail=$((avail+1)); FOUND=$((FOUND+1)); else MISSING_LINES+=("${cat}|${bin}|${method}|${target}"); fi
  done < <(category_tools "$cat")
  printf "  %-10s %2d/%2d available\n" "$cat" "$avail" "$total"
done
echo
info "Coverage: ${FOUND}/${TOTAL} tools already present."
if [[ ${#MISSING_LINES[@]} -gt 0 ]]; then
  info "Missing (first 15): $(printf '%s\n' "${MISSING_LINES[@]}" | cut -d'|' -f2 | head -n 15 | tr '\n' ' ')"
else
  success "All catalogued tools already installed."
fi

# ---------------------------------------------------------------- 4. categories
step "3/7 — Selecting use-cases"
if [[ -n "$CATEGORIES_ARG" ]]; then
  # shellcheck disable=SC2206
  SELECTED_CATS=($CATEGORIES_ARG)
else
  if [[ $YES -eq 1 ]]; then
    SELECTED_CATS=(network web exploit password)
    info "--yes: defaulting to '${SELECTED_CATS[*]}' (override with --categories)."
  else
    echo "Which pentest use-cases do you need? (space-separated)"
    echo "  available: $ALL_CATS all"
    read -r -p "Categories [network web exploit password]: " ans
    ans="${ans:-network web exploit password}"
    # shellcheck disable=SC2206
    SELECTED_CATS=($ans)
  fi
fi
# normalize 'all'
for c in "${SELECTED_CATS[@]}"; do [[ "$c" == "all" ]] && { SELECTED_CATS=($ALL_CATS); break; }; done
# validate
for c in "${SELECTED_CATS[@]}"; do
  [[ " $ALL_CATS " == *" $c "* ]] || die "Unknown category: $c (valid: $ALL_CATS all)"
done
info "Selected: ${SELECTED_CATS[*]}"

# filter missing to selected
declare -a TO_INSTALL=()
for line in "${MISSING_LINES[@]:-}"; do
  cat="${line%%|*}"
  [[ " ${SELECTED_CATS[*]} " == *" $cat "* ]] && TO_INSTALL+=("$line")
done
if [[ $NO_TOOLS -eq 1 ]]; then TO_INSTALL=(); info "--no-tools: skipping tool installs."; fi
info "To install for selected use-cases: ${#TO_INSTALL[@]} package(s)."

# ---------------------------------------------------------------- 5. install helpers
ensure_go() {
  local need=0
  if ! have go; then need=1
  else
    local gv; gv="$(go version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -n1)"
    local gmaj="${gv%%.*}" gmin="${gv#*.}"
    if [[ "${gmaj:-0}" -lt 1 || ( "${gmaj:-0}" -eq 1 && "${gmin:-0}" -lt 23 ) ]]; then need=1; fi
  fi
  if [[ $need -eq 1 ]]; then
    info "Installing official Go ${GO_VERSION} (apt Go is too old for modern security tools)..."
    wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tgz \
      || die "Failed to download Go."
    sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf /tmp/go.tgz
    export PATH="/usr/local/go/bin:${PATH}"
    grep -q '/usr/local/go/bin' "${HOME}/.bashrc" 2>/dev/null || echo 'export PATH="/usr/local/go/bin:$HOME/go/bin:$PATH"' >> "${HOME}/.bashrc"
    success "Go $(go version) installed."
  else
    success "Go OK: $(go version)"
  fi
}

ensure_pipx() { have pipx || { info "Installing pipx..."; sudo apt-get install -y -qq pipx 2>&1 | tail -n 1; pipx ensurepath >/dev/null 2>&1 || true; export PATH="${HOME}/.local/bin:${PATH}"; }; }
ensure_cargo() { have cargo || { info "Installing rust/cargo..."; sudo apt-get install -y -qq cargo rustc 2>&1 | tail -n 1; export PATH="${HOME}/.cargo/bin:${PATH}"; }; }

NEED_GO=0; NEED_PIPX=0; NEED_CARGO=0; NEED_GEM=0
for line in "${TO_INSTALL[@]:-}"; do
  m="$(cut -d'|' -f3 <<<"$line")"
  case "$m" in go) NEED_GO=1;; pipx) NEED_PIPX=1;; cargo) NEED_CARGO=1;; gem) NEED_GEM=1;; esac
done
[[ $NEED_GO -eq 1 ]] && ensure_go
[[ $NEED_PIPX -eq 1 ]] && ensure_pipx
[[ $NEED_CARGO -eq 1 ]] && ensure_cargo
if [[ $NEED_GEM -eq 1 ]]; then have gem || sudo apt-get install -y -qq ruby ruby-dev 2>&1 | tail -n 1; fi

install_one() {
  local bin="$1" method="$2" target="$3"
  case "$method" in
    apt)
      sudo apt-get install -y -qq "$target" 2>&1 | tail -n 1 && success "$bin (apt)" || { err "$bin (apt $target) failed"; return 1; } ;;
    pipx)
      pipx install "$target" 2>&1 | tail -n 1 && success "$bin (pipx)" || { err "$bin (pipx $target) failed"; return 1; } ;;
    go)
      go install "${target}@latest" 2>&1 | tail -n 2 && success "$bin (go)" || { err "$bin (go $target) failed"; return 1; } ;;
    cargo)
      cargo install --locked "$target" 2>&1 | tail -n 2 && success "$bin (cargo)" || { err "$bin (cargo $target) failed"; return 1; } ;;
    gem)
      sudo gem install "$target" 2>&1 | tail -n 1 && success "$bin (gem)" || { err "$bin (gem $target) failed"; return 1; } ;;
    *) err "Unknown method $method for $bin"; return 1 ;;
  esac
}

# ---------------------------------------------------------------- 6. installs
if [[ ${#TO_INSTALL[@]} -gt 0 ]]; then
  step "4/7 — Installing ${#TO_INSTALL[@]} missing tool(s) for: ${SELECTED_CATS[*]}"
  printf '%s\n' "${TO_INSTALL[@]}" | awk -F'|' '{printf "  %-12s %-10s %s (%s)\n", $2, $1, $4, $3}'
  confirm "Install these now?" || die "Aborted by user."
  ok=0; fail=0
  for line in "${TO_INSTALL[@]}"; do
    IFS='|' read -r _cat bin method target <<<"$line"
    if install_one "$bin" "$method" "$target"; then ok=$((ok+1)); else fail=$((fail+1)); fi
  done
  echo; info "Tools: ${GREEN}${ok} installed${RESET}, ${RED}${fail} failed${RESET}."
  [[ $fail -gt 0 ]] && warn "Re-run ./install.sh to retry failures (only missing are retried)."
else
  step "4/7 — No tool installs needed"
  success "Nothing to install."
fi

# ---------------------------------------------------------------- python env
step "5/7 — Setting up Python environment"
if [[ ! -x "$VENV_PY" ]]; then
  info "Creating venv at ${VENV_DIR}..."
  python3 -m venv "$VENV_DIR" || die "venv creation failed."
else
  info "Reusing existing venv."
fi
"$VENV_PIP" install --upgrade -qq pip 2>&1 | tail -n 1 || warn "pip upgrade had warnings."
info "Installing core requirements (pinned mcp v1, no heavy builds)..."
"$VENV_PIP" install -r "${HEXSTRIKE_DIR}/requirements.txt" 2>&1 | tail -n 5 \
  || die "pip install -r requirements.txt failed. See output above."
success "Core Python deps installed."

if [[ $WITH_BROWSER -eq 1 ]]; then info "Installing browser extras..."; "$VENV_PIP" install "selenium>=4.15.0,<5.0.0" "webdriver-manager>=4.0.0,<5.0.0" 2>&1 | tail -n 2 || warn "browser extras failed."; fi
if [[ $WITH_PROXY -eq 1 ]]; then info "Installing proxy extras..."; "$VENV_PIP" install "mitmproxy>=9.0.0,<11.0.0" 2>&1 | tail -n 2 || warn "proxy extras failed."; fi
if [[ $WITH_PWN -eq 1 ]]; then info "Installing pwn extras..."; "$VENV_PIP" install -r "${HEXSTRIKE_DIR}/requirements-optional.txt" 2>&1 | tail -n 3 || warn "pwn extras failed (expected on py3.13)."; fi

# sanity: file-level checks that used to break installs
"$VENV_PY" -m py_compile "${HEXSTRIKE_DIR}/hexstrike_server.py" "${HEXSTRIKE_DIR}/hexstrike_mcp.py" \
  && success "Python syntax OK." || die "Syntax check failed."
"$VENV_PY" -c "from mcp.server.fastmcp import FastMCP; print('MCP v1 FastMCP OK')" 2>/dev/null \
  || "$VENV_PY" -c "from fastmcp import FastMCP; print('standalone fastmcp OK')" 2>/dev/null \
  || warn "MCP import check failed — re-run pip install or check Python version."

if [[ $WITH_OPENCODE -eq 1 ]]; then
  if have npm; then info "Installing OpenCode..."; npm i -g opencode-ai 2>&1 | tail -n 2 || warn "opencode npm install failed.";
  else warn "--with-opencode requested but npm not found. Install nodejs first."; fi
fi

# ---------------------------------------------------------------- MCP config
step "6/7 — Writing MCP client config (fixes placeholder + timeout bugs)"
mkdir -p "$OC_CONFIG_DIR"
if [[ -f "${OC_CONFIG_DIR}/opencode.jsonc" ]]; then
  bak="${OC_CONFIG_DIR}/opencode.jsonc.bak.$(date +%s)"
  mv "${OC_CONFIG_DIR}/opencode.jsonc" "$bak"
  warn "opencode.jsonc overrides opencode.json — backed up to $bak"
fi
cat > "$OC_CONFIG" <<EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "mcp": {
    "hexstrike": {
      "type": "local",
      "command": [
        "${VENV_PY}",
        "${HEXSTRIKE_DIR}/hexstrike_mcp.py",
        "--server",
        "http://localhost:${SERVER_PORT}",
        "--health-timeout",
        "15",
        "--lazy"
      ],
      "enabled": true
    }
  }
}
EOF
if have jq && jq empty "$OC_CONFIG" >/dev/null 2>&1; then success "OpenCode config written + JSON valid: ${OC_CONFIG}";
else success "OpenCode config written: ${OC_CONFIG}"; fi
info "Claude Desktop / Cursor users: copy command/args from hexstrike-ai-mcp.json (paths already fixed by installer if you re-run with sed below)."

# ---------------------------------------------------------------- validation
step "7/7 — Validating"
ok=0; fail=0
check() { local label="$1"; shift; if "$@" >/dev/null 2>&1; then success "$label"; ok=$((ok+1)); else err "$label"; fail=$((fail+1)); fi; }
check "python3 present" command -v python3
check "venv python present" test -x "$VENV_PY"
check "venv has mcp module" "$VENV_PY" -c "import mcp"
check "server syntax" "$VENV_PY" -m py_compile "${HEXSTRIKE_DIR}/hexstrike_server.py"
check "mcp client syntax" "$VENV_PY" -m py_compile "${HEXSTRIKE_DIR}/hexstrike_mcp.py"
check "opencode config valid" test -f "$OC_CONFIG"
echo; info "Validation: ${GREEN}${ok} passed${RESET}, ${RED}${fail} failed${RESET}."

if [[ $CHECK_HEALTH -eq 1 ]]; then
  info "Live health check on port ${SERVER_PORT}..."
  if have tmux; then
    tmux kill-session -t hexstrike 2>/dev/null || true
    tmux new-session -d -s hexstrike "cd '${HEXSTRIKE_DIR}' && '${VENV_PY}' hexstrike_server.py --port ${SERVER_PORT}"
  else
    nohup "$VENV_PY" "${HEXSTRIKE_DIR}/hexstrike_server.py" --port "$SERVER_PORT" >/tmp/hexstrike-server.log 2>&1 &
    echo $! > /tmp/hexstrike-server.pid
  fi
  healthy=0
  for _ in $(seq 1 25); do curl -sf "http://localhost:${SERVER_PORT}/health" >/dev/null 2>&1 && { healthy=1; break; }; sleep 1; done
  if [[ $healthy -eq 1 ]]; then
    success "Server responding on :${SERVER_PORT}."
    curl -s "http://localhost:${SERVER_PORT}/health" | "$VENV_PY" -c "
import json,sys
d=json.load(sys.stdin)
print(f\"  version : {d.get('version')} ({d.get('detection','?')})\")
for c,s in sorted(d.get('category_stats',{}).items()):
    print(f\"  {c:12} {s['available']}/{s['total']}\")
print(f\"  TOTAL       {d.get('total_tools_available')}/{d.get('total_tools_count')}\")
missing=d.get('missing_essential_tools',[])
print('  missing essential:', ', '.join(missing) if missing else 'none')
" 2>/dev/null || warn "Could not parse health JSON."
    info "Server left running (tmux attach -t hexstrike, or kill /tmp/hexstrike-server.pid)."
  else
    err "Server did not respond in 25s. Logs: tmux attach -t hexstrike OR tail /tmp/hexstrike-server.log"
  fi
fi

# ---------------------------------------------------------------- guide
cat <<EOF

${BOLD}${GREEN}Done.${RESET} Run guide:
  1. Start server :  cd '${HEXSTRIKE_DIR}' && source hexstrike-env/bin/activate && python3 hexstrike_server.py --port ${SERVER_PORT}
  2. Health check :  curl -s http://localhost:${SERVER_PORT}/health | python3 -m json.tool | head -n 40
  3. AI client     :  OpenCode already configured at ${OC_CONFIG} (restart OpenCode).
  4. Re-scan tools :  ./install.sh --categories "network web" --yes
  5. Extras        :  ./install.sh --with-browser | --with-proxy | --with-pwn | --with-all

Fixed in v6.0.1: installer created, requirements unblocked, /health fast+accurate,
MCP 15s+lazy handshake, opencode.json auto-written.
EOF
