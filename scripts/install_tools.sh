#!/usr/bin/env bash
# =============================================================================
#  HexStrike AI — Security Tools Installer
#  Version: 1.0.0
#  Compatibility: Linux (Debian/Ubuntu, Arch, Fedora/RHEL) | macOS (Homebrew)
# =============================================================================
#
#  USAGE:
#    ./scripts/install_tools.sh [OPTIONS]
#
#  OPTIONS:
#    --only <category>   Install only a specific category
#                        Categories: network, web, auth, binary, cloud, ctf, osint, browser
#    --dry-run           Preview what would be installed, without making changes
#    --show-log          Display full install log at the end
#    --list              List all categories and their tools, then exit
#    --help, -h          Show this help message and exit
#
#  EXAMPLES:
#    ./scripts/install_tools.sh                   # Install everything
#    ./scripts/install_tools.sh --only network    # Install only network tools
#    ./scripts/install_tools.sh --dry-run         # Preview all installs
#    ./scripts/install_tools.sh --only web --dry-run
#
#  NOTES:
#    - Python deps (requirements.txt) are handled separately: pip install -r requirements.txt
#    - GUI tools (Ghidra, Maltego, Binary Ninja, IDA) are skipped with guidance
#    - All pip installs use --user flag (no root required)
#    - Go packages install to ~/go/bin (add to PATH if not already set)
#    - Cargo packages install to ~/.cargo/bin (add to PATH if not already set)
#    - Gem installs use --user-install flag (no root required)
#    - apt/dnf/pacman installs still require sudo (no user-level equivalent)
# =============================================================================

set -uo pipefail

# ─── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# ─── Globals ─────────────────────────────────────────────────────────────────
DRY_RUN=false
SHOW_LOG=false
ONLY_CATEGORY=""
FAIL_HINT=""
LOG_FILE="$(pwd)/install_log.txt"

COUNT_INSTALLED=0
COUNT_SKIPPED=0
COUNT_ALREADY=0
COUNT_FAILED=0
COUNT_MANUAL=0

declare -a FAILED_TOOLS=()
declare -a MANUAL_TOOLS=()
declare -A FAILED_REASONS=()

# ─── Detected OS/Package-Manager ─────────────────────────────────────────────
OS=""          # linux | macos
PKG_MGR=""     # apt | dnf | pacman | brew | unknown
DISTRO=""      # ubuntu | debian | arch | fedora | rhel | unknown

# ─── Sudo Wrapper ─────────────────────────────────────────────────────────────
# Empty when already running as root (e.g. Docker containers). Using an empty
# variable avoids 'sudo: command not found' errors in minimal environments.
SUDO="sudo"
[[ "$(id -u)" == "0" ]] && SUDO=""

# ─── Banner ──────────────────────────────────────────────────────────────────
print_banner() {
  echo -e "${RED}${BOLD}"
  cat << 'EOF'
  ██╗  ██╗███████╗██╗  ██╗███████╗████████╗██████╗ ██╗██╗  ██╗███████╗
  ██║  ██║██╔════╝╚██╗██╔╝██╔════╝╚══██╔══╝██╔══██╗██║██║ ██╔╝██╔════╝
  ███████║█████╗   ╚███╔╝ ███████╗   ██║   ██████╔╝██║█████╔╝ █████╗
  ██╔══██║██╔══╝   ██╔██╗ ╚════██║   ██║   ██╔══██╗██║██╔═██╗ ██╔══╝
  ██║  ██║███████╗██╔╝ ██╗███████║   ██║   ██║  ██║██║██║  ██╗███████╗
  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚══════╝
EOF
  echo -e "${RESET}${CYAN}${BOLD}           AI-Powered Penetration Testing Framework — Tool Installer${RESET}"
  echo -e "${DIM}           https://github.com/0x4m4/hexstrike-ai${RESET}"
  echo ""
}

# ─── Logging ─────────────────────────────────────────────────────────────────
log() {
  local timestamp
  # Guard against I/O errors (e.g. disk full in Docker) — never crash on logging
  timestamp="$(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '----')"
  echo "[$timestamp] $*" >> "$LOG_FILE" 2>/dev/null || true
}

info()    { echo -e "${CYAN}[i]${RESET} $*";                    log "[INFO]    $*"; }
success() { echo -e "${GREEN}[✔]${RESET} $*";                   log "[SUCCESS] $*"; }
warn()    { echo -e "${YELLOW}[!]${RESET} $*";                  log "[WARN]    $*"; }
error()   { echo -e "${RED}[✘]${RESET} $*" >&2;                log "[ERROR]   $*"; }
skip()    { echo -e "${DIM}[~]${RESET} ${DIM}$*${RESET}";      log "[SKIP]    $*"; }
manual()  { echo -e "${MAGENTA}[⊕]${RESET} $*";                log "[MANUAL]  $*"; }
dry()     { echo -e "${BLUE}[•]${RESET} ${BLUE}[DRY-RUN]${RESET} would install: ${BOLD}$*${RESET}"; log "[DRY-RUN] $*"; }
section() { echo ""; echo -e "${BOLD}${YELLOW}━━━ $* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

# ─── Help ─────────────────────────────────────────────────────────────────────
print_help() {
  print_banner
  echo -e "${BOLD}USAGE${RESET}"
  echo "  ./scripts/install_tools.sh [OPTIONS]"
  echo ""
  echo -e "${BOLD}OPTIONS${RESET}"
  echo "  --only <category>   Install only a specific category of tools"
  echo "  --dry-run           Preview what would be installed without making changes"
  echo "  --show-log          Display full install log at the end"
  echo "  --list              List all categories and tools, then exit"
  echo "  --help, -h          Show this help message"
  echo ""
  echo -e "${BOLD}CATEGORIES${RESET}"
  echo "  network   Network reconnaissance & scanning tools (25+)"
  echo "  web       Web application security testing tools (40+)"
  echo "  auth      Authentication & password cracking tools (12+)"
  echo "  binary    Binary analysis & reverse engineering tools (25+)"
  echo "  cloud     Cloud & container security tools (20+)"
  echo "  ctf       CTF & digital forensics tools (20+)"
  echo "  osint     OSINT & intelligence gathering tools (20+)"
  echo "  browser   Browser agent dependencies (Chromium + ChromeDriver)"
  echo ""
  echo -e "${BOLD}EXAMPLES${RESET}"
  echo "  ./scripts/install_tools.sh                    Install all tools"
  echo "  ./scripts/install_tools.sh --only web         Install only web tools"
  echo "  ./scripts/install_tools.sh --dry-run          Preview all installs"
  echo "  ./scripts/install_tools.sh --only cloud --dry-run"
  echo ""
  echo -e "${BOLD}NOTES${RESET}"
  echo "  • Python deps: handle separately with  pip3 install -r requirements.txt"
  echo "  • Logs are written to: $LOG_FILE"
  echo "  • Go tools are installed to ~/go/bin — ensure it is in your PATH"
  echo "  • Rust/Cargo tools are installed to ~/.cargo/bin — ensure it is in your PATH"
  echo "  • Gem tools use --user-install — ensure ~/.gem/ruby/*/bin is in your PATH"
  echo "  • pip tools use --user — ~/.local/bin should be in your PATH"
}

# ─── Tool List ────────────────────────────────────────────────────────────────
print_list() {
  print_banner
  echo -e "${BOLD}HexStrike AI — Managed Tool Inventory${RESET}"
  echo ""
  echo -e "${CYAN}🔍 NETWORK / RECON (25+)${RESET}"
  echo "   nmap, masscan, rustscan, autorecon, amass, subfinder, nuclei,"
  echo "   fierce, dnsenum, theharvester, responder, netexec, enum4linux,"
  echo "   enum4linux-ng, arp-scan, nbtscan, smbmap"
  echo ""
  echo -e "${CYAN}🌐 WEB APPLICATION SECURITY (40+)${RESET}"
  echo "   gobuster, ffuf, feroxbuster, dirsearch, dirb, httpx, katana,"
  echo "   hakrawler, gau, waybackurls, nikto, sqlmap, wpscan, arjun,"
  echo "   paramspider, dalfox, wafw00f, whatweb, jwt-tool, wfuzz, commix"
  echo ""
  echo -e "${CYAN}🔐 AUTH / PASSWORD (12+)${RESET}"
  echo "   hydra, john, hashcat, medusa, patator, evil-winrm, hash-identifier"
  echo ""
  echo -e "${CYAN}🔬 BINARY / REVERSE ENGINEERING (25+)${RESET}"
  echo "   gdb, radare2, binwalk, ropgadget, checksec, exiftool, volatility3,"
  echo "   strings/objdump/readelf (binutils)"
  echo ""
  echo -e "${MAGENTA}   ⊕ MANUAL INSTALL REQUIRED: ghidra, ida-free, binary-ninja${RESET}"
  echo ""
  echo -e "${CYAN}☁️  CLOUD / CONTAINER (20+)${RESET}"
  echo "   prowler, trivy, kube-hunter, kube-bench, checkov, aws-cli,"
  echo "   kubectl, helm, docker-bench-security"
  echo ""
  echo -e "${CYAN}🏆 CTF / FORENSICS (20+)${RESET}"
  echo "   volatility3, foremost, steghide, exiftool, binwalk, scalpel,"
  echo "   testdisk, photorec, zsteg, stegsolve, outguess, bulk-extractor"
  echo ""
  echo -e "${CYAN}🕵️  OSINT / INTELLIGENCE (20+)${RESET}"
  echo "   sherlock, recon-ng, spiderfoot, theharvester"
  echo ""
  echo -e "${MAGENTA}   ⊕ MANUAL INSTALL REQUIRED: maltego, shodan-cli (API key needed)${RESET}"
  echo ""
  echo -e "${CYAN}🌍 BROWSER AGENT${RESET}"
  echo "   chromium, chromedriver"
}

# ─── OS Detection ─────────────────────────────────────────────────────────────
detect_os() {
  section "Detecting Operating System"

  if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    PKG_MGR="brew"
    DISTRO="macos"
    info "Detected: ${BOLD}macOS${RESET}"
    if ! command -v brew &>/dev/null; then
      error "Homebrew is not installed. Install it first: https://brew.sh"
      error "Run: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
      exit 1
    fi
    info "Homebrew found: $(brew --version | head -1)"

  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if [[ -f /etc/os-release ]]; then
      # shellcheck source=/dev/null
      source /etc/os-release
      DISTRO="${ID:-unknown}"
    fi

    case "$DISTRO" in
      ubuntu|debian|kali|parrot|pop|mint|linuxmint)
        PKG_MGR="apt"
        # Suppress ALL interactive prompts from apt/dpkg (crucial for Docker/CI)
        export DEBIAN_FRONTEND=noninteractive
        export DEBCONF_NONINTERACTIVE_SEEN=true
        info "Detected: ${BOLD}${DISTRO^} Linux${RESET} (apt)"
        ;;
      arch|manjaro|endeavouros|garuda)
        PKG_MGR="pacman"
        info "Detected: ${BOLD}${DISTRO^} Linux${RESET} (pacman)"
        ;;
      fedora|rhel|centos|rocky|alma)
        PKG_MGR="dnf"
        info "Detected: ${BOLD}${DISTRO^} Linux${RESET} (dnf)"
        ;;
      *)
        PKG_MGR="unknown"
        warn "Unknown Linux distro: ${DISTRO}. System package installs will be skipped."
        warn "Go, pip, cargo, and gem installs will still proceed."
        ;;
    esac
  else
    error "Unsupported OS: $OSTYPE"
    exit 1
  fi

  log "OS=$OS DISTRO=$DISTRO PKG_MGR=$PKG_MGR"
}

# ─── PATH Guidance ────────────────────────────────────────────────────────────
check_paths() {
  section "Checking User PATH"
  local missing_paths=()

  # Go
  if command -v go &>/dev/null; then
    local gopath
    gopath="$(go env GOPATH 2>/dev/null || echo "$HOME/go")"
    if [[ ":$PATH:" != *":${gopath}/bin:"* ]]; then
      missing_paths+=("${gopath}/bin  (Go binaries)")
    fi
  fi

  # Cargo / Rust
  if [[ -d "$HOME/.cargo/bin" && ":$PATH:" != *":$HOME/.cargo/bin:"* ]]; then
    missing_paths+=("$HOME/.cargo/bin  (Rust/Cargo binaries)")
  fi

  # pip --user
  local pip_bin
  pip_bin="$(python3 -m site --user-base 2>/dev/null)/bin"
  if [[ -d "$pip_bin" && ":$PATH:" != *":${pip_bin}:"* ]]; then
    missing_paths+=("${pip_bin}  (pip --user binaries)")
  fi

  # Gem user install
  if command -v ruby &>/dev/null; then
    local gem_bin
    gem_bin="$(ruby -e 'puts Gem.user_dir' 2>/dev/null)/bin"
    if [[ -d "$gem_bin" && ":$PATH:" != *":${gem_bin}:"* ]]; then
      missing_paths+=("${gem_bin}  (gem --user-install binaries)")
    fi
  fi

  if [[ ${#missing_paths[@]} -gt 0 ]]; then
    warn "The following directories are NOT in your PATH. Add them to ~/.bashrc or ~/.zshrc:"
    for p in "${missing_paths[@]}"; do
      warn "  export PATH=\"\$PATH:${p%%  *}\""
    done
    echo ""
  else
    success "All known user bin directories are in PATH"
  fi
}

# ─── Prereq Installers ────────────────────────────────────────────────────────

# Install python3 + pip3
_install_python() {
  echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}python3 & pip3${RESET} ... "
  local ok=false
  case "$PKG_MGR" in
    apt)
      $SUDO apt-get install -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        python3 python3-pip python3-dev &>/dev/null && ok=true ;;
    dnf)
      $SUDO dnf install -y python3 python3-pip &>/dev/null && ok=true ;;
    pacman)
      $SUDO pacman -S --noconfirm python python-pip &>/dev/null && ok=true ;;
    brew)
      brew install python3 &>/dev/null && ok=true ;;
  esac
  if $ok && command -v python3 &>/dev/null; then
    echo -e "${GREEN}done${RESET}"
    log "[SUCCESS] python3 & pip3 installed"
  else
    echo -e "${RED}failed${RESET}"
    error "Could not install python3 — please install it manually."
    exit 1
  fi
}

# Install git
_install_git() {
  echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}git${RESET} ... "
  local ok=false
  case "$PKG_MGR" in
    apt)    $SUDO apt-get install -y \
              -o Dpkg::Options::="--force-confdef" \
              -o Dpkg::Options::="--force-confold" \
              git &>/dev/null && ok=true ;;
    dnf)    $SUDO dnf install -y git &>/dev/null && ok=true ;;
    pacman) $SUDO pacman -S --noconfirm git &>/dev/null && ok=true ;;
    brew)   brew install git &>/dev/null && ok=true ;;
  esac
  if $ok && command -v git &>/dev/null; then
    echo -e "${GREEN}done${RESET}"
    log "[SUCCESS] git installed"
  else
    echo -e "${RED}failed${RESET}"
    error "Could not install git — please install it manually."
    exit 1
  fi
}

# Install Go — prefer package manager; fall back to official binary on Linux
_install_go() {
  echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}Go${RESET} ... "

  if [[ "$OS" == "macos" ]]; then
    brew install go &>/dev/null
    if command -v go &>/dev/null; then
      echo -e "${GREEN}done (brew)${RESET}"
      log "[SUCCESS] go installed via brew"
      return
    fi
  else
    # Try package manager first
    local pkg_ok=false
    case "$PKG_MGR" in
      apt)    $SUDO apt-get install -y \
                -o Dpkg::Options::="--force-confdef" \
                -o Dpkg::Options::="--force-confold" \
                golang-go &>/dev/null && pkg_ok=true ;;
      dnf)    $SUDO dnf install -y golang &>/dev/null && pkg_ok=true ;;
      pacman) $SUDO pacman -S --noconfirm go &>/dev/null && pkg_ok=true ;;
    esac

    if $pkg_ok && command -v go &>/dev/null; then
      echo -e "${GREEN}done (pkg)${RESET}"
      log "[SUCCESS] go installed via package manager"
      return
    fi

    # Fall back: download official binary to ~/.local/go
    echo -e "${YELLOW}pkg failed — downloading official binary...${RESET}"
    echo -ne "  ${CYAN}↳${RESET} Fetching latest Go release ... "
    local go_ver
    go_ver=$(curl -sL "https://go.dev/VERSION?m=text" | head -1)
    local arch
    arch=$(uname -m); [[ "$arch" == "x86_64" ]] && arch="amd64" || arch="arm64"
    local go_url="https://go.dev/dl/${go_ver}.linux-${arch}.tar.gz"

    mkdir -p "$HOME/.local"
    if curl -sL "$go_url" | tar -C "$HOME/.local" -xz 2>/dev/null; then
      # Symlink binaries into ~/.local/bin
      mkdir -p "$HOME/.local/bin"
      ln -sf "$HOME/.local/go/bin/go"   "$HOME/.local/bin/go"
      ln -sf "$HOME/.local/go/bin/gofmt" "$HOME/.local/bin/gofmt"
      # Make available in current shell immediately
      export PATH="$HOME/.local/bin:$PATH"
      if command -v go &>/dev/null; then
        echo -e "${GREEN}done (${go_ver} → ~/.local/go)${RESET}"
        log "[SUCCESS] go ${go_ver} installed to ~/.local/go"
        return
      fi
    fi
  fi

  echo -e "${RED}failed${RESET}"
  warn "Could not install Go — Go-based tools will be skipped."
  log "[WARN] go install failed"
}

# Install Rust + Cargo via rustup (user-level, no root)
_install_rust() {
  echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}Rust & Cargo${RESET} via rustup ... "
  if curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
      | sh -s -- -y --no-modify-path &>/dev/null; then
    # Source cargo env so cargo is available immediately in this session
    # shellcheck source=/dev/null
    [[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"
    export PATH="$HOME/.cargo/bin:$PATH"
    if command -v cargo &>/dev/null; then
      echo -e "${GREEN}done ($(cargo --version))${RESET}"
      log "[SUCCESS] rust & cargo installed via rustup"
      return
    fi
  fi
  echo -e "${RED}failed${RESET}"
  warn "Could not install Rust — Cargo-based tools will be skipped."
  log "[WARN] rustup install failed"
}

# Install Ruby
_install_ruby() {
  echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}Ruby${RESET} ... "
  local ok=false
  case "$PKG_MGR" in
    apt)    $SUDO apt-get install -y \
              -o Dpkg::Options::="--force-confdef" \
              -o Dpkg::Options::="--force-confold" \
              ruby ruby-dev ruby-rubygems &>/dev/null && ok=true ;;
    dnf)    $SUDO dnf install -y ruby ruby-devel &>/dev/null && ok=true ;;
    pacman) $SUDO pacman -S --noconfirm ruby &>/dev/null && ok=true ;;
    brew)   brew install ruby &>/dev/null && ok=true ;;
  esac
  if $ok && command -v ruby &>/dev/null; then
    echo -e "${GREEN}done ($(ruby --version | awk '{print $2}'))${RESET}"
    log "[SUCCESS] ruby installed"
  else
    echo -e "${RED}failed${RESET}"
    warn "Could not install Ruby — gem-based tools will be skipped."
    log "[WARN] ruby install failed"
  fi
}

# ─── Bootstrap Essential Tools ────────────────────────────────────────────────
# Installs curl, ca-certificates, gnupg, lsb-release BEFORE any other step.
# These are needed by Go/Rust/Trivy downloaders and repo setup.
# Uses apt/brew directly (no curl required for this step).
bootstrap_essentials() {
  if [[ "$DRY_RUN" == true ]]; then
    return
  fi

  local need=()
  command -v curl        &>/dev/null || need+=("curl")
  command -v gpg         &>/dev/null || need+=("gpg")

  if [[ ${#need[@]} -eq 0 ]]; then
    return  # Nothing to bootstrap
  fi

  section "Bootstrapping Essential Tools"
  info "Installing: ${need[*]} (required for downloaders and repo setup)"

  case "$PKG_MGR" in
    apt)
      echo -ne "  ${CYAN}↳${RESET} Running apt-get update (bootstrap) ... "
      $SUDO apt-get update -qq &>/dev/null \
        && echo -e "${GREEN}done${RESET}" \
        || echo -e "${YELLOW}skipped${RESET}"
      echo -ne "  ${CYAN}↳${RESET} Installing curl, ca-certificates, gnupg, lsb-release ... "
      if $SUDO apt-get install -y \
          -o Dpkg::Options::="--force-confdef" \
          -o Dpkg::Options::="--force-confold" \
          curl ca-certificates gnupg lsb-release &>/dev/null; then
        echo -e "${GREEN}done${RESET}"
        log "[SUCCESS] bootstrap essentials installed"
      else
        echo -e "${RED}failed${RESET}"
        warn "Could not install bootstrap tools — some installers may fail"
      fi
      ;;
    dnf)
      echo -ne "  ${CYAN}↳${RESET} Installing curl, ca-certificates, gnupg ... "
      if $SUDO dnf install -y curl ca-certificates gnupg &>/dev/null; then
        echo -e "${GREEN}done${RESET}"
      else
        echo -e "${RED}failed${RESET}"
      fi
      ;;
    pacman)
      echo -ne "  ${CYAN}↳${RESET} Installing curl, ca-certificates, gnupg ... "
      if $SUDO pacman -S --noconfirm curl ca-certificates gnupg &>/dev/null; then
        echo -e "${GREEN}done${RESET}"
      else
        echo -e "${RED}failed${RESET}"
      fi
      ;;
    brew)
      # macOS: curl is bundled with the OS, nothing to do
      ;;
  esac
}

# ─── Prereq Checks & Auto-Install ─────────────────────────────────────────────
check_prerequisites() {
  section "Checking & Installing Prerequisites"

  # ── python3 + pip3 (hard required) ──
  if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
    _install_python
  else
    success "python3 $(python3 --version 2>&1 | awk '{print $2}') — already installed"
  fi

  # ── git (hard required) ──
  if ! command -v git &>/dev/null; then
    _install_git
  else
    success "git $(git --version | awk '{print $3}') — already installed"
  fi

  # ── Go (optional — needed for many tools) ──
  if ! command -v go &>/dev/null; then
    _install_go
  else
    success "go $(go version | awk '{print $3}') — already installed"
  fi

  # ── Rust / Cargo (optional — rustscan, feroxbuster) ──
  if ! command -v cargo &>/dev/null; then
    # Source cargo env in case rustup was already run but PATH not updated
    [[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env" 2>/dev/null || true
    if ! command -v cargo &>/dev/null; then
      _install_rust
    else
      success "cargo $(cargo --version) — already installed"
    fi
  else
    success "cargo $(cargo --version) — already installed"
  fi

  # ── Ruby (optional — wpscan, evil-winrm, zsteg) ──
  if ! command -v ruby &>/dev/null; then
    _install_ruby
  else
    success "ruby $(ruby --version | awk '{print $2}') — already installed"
  fi
}

# ─── Setup PATH ───────────────────────────────────────────────────────────────
# Ensure Go, pip, cargo, gem bin directories are in PATH so tool_exists finds
# binaries immediately after installation.
setup_paths() {
  mkdir -p "$HOME/.local/bin" 2>/dev/null || true
  export PATH="$HOME/.local/bin:$PATH"

  if command -v go &>/dev/null; then
    local gobin
    gobin="$(go env GOPATH 2>/dev/null || echo "$HOME/go")/bin"
    mkdir -p "$gobin" 2>/dev/null || true
    export PATH="$gobin:$PATH"
  fi

  if [[ -d "$HOME/.cargo/bin" ]]; then
    export PATH="$HOME/.cargo/bin:$PATH"
  fi

  if command -v ruby &>/dev/null; then
    local gembin
    gembin="$(ruby -e 'puts Gem.user_dir' 2>/dev/null)/bin"
    mkdir -p "$gembin" 2>/dev/null || true
    export PATH="$gembin:$PATH"
  fi
}

# ─── Install Helpers ──────────────────────────────────────────────────────────

# Check if a tool is already installed
tool_exists() {
  local cmd="$1"
  command -v "$cmd" &>/dev/null
}

# Package manager install (apt/dnf/pacman/brew)
# apt calls use -o Dpkg::Options to suppress config-file prompts in Docker/CI.
_pkg_install() {
  local pkg="$1"
  case "$PKG_MGR" in
    apt)    $SUDO apt-get install -y \
              -o Dpkg::Options::="--force-confdef" \
              -o Dpkg::Options::="--force-confold" \
              "$pkg" &>/dev/null ;;
    dnf)    $SUDO dnf install -y "$pkg" &>/dev/null ;;
    pacman) $SUDO pacman -S --noconfirm "$pkg" &>/dev/null ;;
    brew)   brew install "$pkg" &>/dev/null ;;
    *)      return 1 ;;
  esac
}

# pip --user install
# Falls back to --break-system-packages for PEP 668 (Ubuntu 24.04+, Kali etc.)
_pip_install() {
  pip3 install --user --quiet "$1" 2>/dev/null || \
  pip3 install --user --quiet --break-system-packages "$1" 2>/dev/null
}

# go install
# Always cleans build cache + module cache after each install to prevent
# disk exhaustion in space-constrained environments (Docker, CI, VMs).
# The installed binary in $GOPATH/bin is preserved; only caches are removed.
_go_install() {
  command -v go &>/dev/null || return 1
  local ret=0
  go install "$1" 2>/dev/null || ret=1
  # Free Go disk usage immediately — binary is already placed in GOPATH/bin
  go clean -cache -modcache 2>/dev/null || true
  return $ret
}

# cargo install
_cargo_install() {
  command -v cargo &>/dev/null || return 1
  cargo install --quiet "$1" 2>/dev/null
}

# gem --user-install
_gem_install() {
  command -v gem &>/dev/null || return 1
  gem install --user-install --no-document --quiet "$1" 2>/dev/null
}

# git clone (shallow) to a target directory
_git_install() {
  local url="$1"
  local dir="$2"
  command -v git &>/dev/null || return 1
  mkdir -p "$(dirname "$dir")" 2>/dev/null || true
  rm -rf "$dir" 2>/dev/null || true
  git clone --depth 1 --quiet "$url" "$dir" 2>/dev/null
}

# Create a wrapper script in ~/.local/bin for a git-cloned tool
_make_wrapper() {
  local name="$1"    # binary name
  local run_cmd="$2"  # e.g. "python3 /path/to/tool.py"
  mkdir -p "$HOME/.local/bin"
  cat > "$HOME/.local/bin/$name" <<WRAP
#!/usr/bin/env bash
exec $run_cmd "\$@"
WRAP
  chmod +x "$HOME/.local/bin/$name"
}

# ─── Master Install Function ──────────────────────────────────────────────────
# install_tool <display_name> <check_command> <method> <pkg_or_module>
#   method: pkg | pip | go | cargo | gem
install_tool() {
  local name="$1"
  local check_cmd="$2"
  local method="$3"
  local target="$4"

  if tool_exists "$check_cmd"; then
    skip "$name — already installed ($(command -v "$check_cmd"))"
    (( COUNT_ALREADY++ )) || true
    return 0
  fi

  if [[ "$DRY_RUN" == true ]]; then
    dry "$name  (via $method: $target)"
    return 0
  fi

  echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}$name${RESET} via ${method} ... "

  local ok=false
  case "$method" in
    pkg)   _pkg_install "$target"    && ok=true ;;
    pip)   _pip_install "$target"    && ok=true ;;
    go)    _go_install "$target"     && ok=true ;;
    cargo) _cargo_install "$target"  && ok=true ;;
    gem)   _gem_install "$target"    && ok=true ;;
  esac

  if [[ "$ok" == true ]] && tool_exists "$check_cmd"; then
    echo -e "${GREEN}done${RESET}"
    success "$name installed successfully"
    (( COUNT_INSTALLED++ )) || true
  else
    echo -e "${RED}failed${RESET}"
    error "$name install failed (method: $method, target: $target)"
    FAILED_TOOLS+=("$name")
    (( COUNT_FAILED++ )) || true
  fi
}

# install_tool_multi — try multiple install methods in order, stop at first success
# install_tool_multi <name> <check_cmd> <"method:target" ...>
install_tool_multi() {
  local name="$1"
  local check_cmd="$2"
  shift 2
  local methods=("$@")

  if tool_exists "$check_cmd"; then
    skip "$name — already installed ($(command -v "$check_cmd"))"
    (( COUNT_ALREADY++ )) || true
    return 0
  fi

  if [[ "$DRY_RUN" == true ]]; then
    local first="${methods[0]}"
    dry "$name  (preferred: ${first%%:*}: ${first#*:})"
    return 0
  fi

  echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}$name${RESET} ... "

  for entry in "${methods[@]}"; do
    local method="${entry%%:*}"
    local target="${entry#*:}"
    local ok=false

    case "$method" in
      pkg)   _pkg_install "$target"   && ok=true ;;
      pip)   _pip_install "$target"   && ok=true ;;
      go)    _go_install "$target"    && ok=true ;;
      cargo) _cargo_install "$target" && ok=true ;;
      gem)   _gem_install "$target"   && ok=true ;;
    esac

    if [[ "$ok" == true ]] && tool_exists "$check_cmd"; then
      echo -e "${GREEN}done${RESET} (via $method)"
      success "$name installed successfully via $method"
      (( COUNT_INSTALLED++ )) || true
      return 0
    fi
  done

  # Build auto-reason from methods tried
  local tried=""
  for entry in "${methods[@]}"; do
    local m="${entry%%:*}"
    case "$m" in
      pkg)   tried+="not in repos, " ;;
      pip)   tried+="pip failed, " ;;
      go)    tried+="go build failed, " ;;
      cargo) tried+="cargo build failed, " ;;
      gem)   tried+="gem failed, " ;;
    esac
  done
  tried="${tried%, }"
  local reason="${FAIL_HINT:-$tried}"
  FAIL_HINT=""

  echo -e "${RED}failed${RESET}"
  error "$name: $reason"
  FAILED_TOOLS+=("$name")
  FAILED_REASONS["$name"]="$reason"
  (( COUNT_FAILED++ )) || true
}

# skip_manual_install — for GUI/manual tools
skip_manual_install() {
  local name="$1"
  local url="$2"
  manual "$name — requires manual install. Download from: ${BOLD}$url${RESET}"
  MANUAL_TOOLS+=("$name  →  $url")
  (( COUNT_MANUAL++ )) || true
  log "[MANUAL] $name — $url"
}

# ─── Category: Network / Recon ───────────────────────────────────────────────
install_network() {
  section "🔍 Network Reconnaissance & Scanning Tools"

  install_tool_multi "nmap" "nmap" \
    "pkg:nmap"

  install_tool_multi "masscan" "masscan" \
    "pkg:masscan"

  # rustscan: cargo (user-level) or brew on macOS
  if [[ "$OS" == "macos" ]]; then
    install_tool_multi "rustscan" "rustscan" \
      "brew:rustscan" \
      "cargo:rustscan"
  else
    install_tool_multi "rustscan" "rustscan" \
      "cargo:rustscan"
  fi

  # amass: fixed go install path (v4 cmd/amass)
  install_tool_multi "amass" "amass" \
    "pkg:amass" \
    "go:github.com/owasp-amass/amass/v4/cmd/amass@latest"

  # subfinder: try apt first, then go install
  install_tool_multi "subfinder" "subfinder" \
    "pkg:subfinder" \
    "go:github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"

  # nuclei — go install
  install_tool_multi "nuclei" "nuclei" \
    "go:github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"

  # fierce — pip (Python tool)
  install_tool_multi "fierce" "fierce" \
    "pip:fierce" \
    "pkg:fierce"

  # dnsenum — apt/brew
  install_tool_multi "dnsenum" "dnsenum" \
    "pkg:dnsenum"

  # theharvester — pip; git clone fallback
  if ! tool_exists theHarvester && ! tool_exists theharvester; then
    FAIL_HINT="pip/pkg failed; try: git clone https://github.com/laramies/theHarvester"
    install_tool_multi "theharvester" "theHarvester" \
      "pip:theHarvester" \
      "pkg:theharvester"
  else
    skip "theharvester — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # responder — Kali-only pkg; git clone fallback
  if ! tool_exists responder; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "responder (via pkg or git clone)"
    else
      echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}responder${RESET} ... "
      local resp_ok=false
      _pkg_install responder &>/dev/null && tool_exists responder && resp_ok=true
      if [[ "$resp_ok" != true ]]; then
        if _git_install "https://github.com/lgandx/Responder.git" "$HOME/.local/share/responder"; then
          pip3 install --user --quiet netifaces 2>/dev/null || \
          pip3 install --user --quiet --break-system-packages netifaces 2>/dev/null || true
          _make_wrapper "responder" "python3 $HOME/.local/share/responder/Responder.py"
          tool_exists responder && resp_ok=true
        fi
      fi
      if [[ "$resp_ok" == true ]]; then
        echo -e "${GREEN}done${RESET}"
        success "responder installed"
        (( COUNT_INSTALLED++ )) || true
      else
        echo -e "${RED}failed${RESET}"
        error "responder: Kali-only; git clone also failed"
        FAILED_TOOLS+=("responder")
        FAILED_REASONS["responder"]="Kali-only pkg; git clone failed"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "responder — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # netexec (formerly crackmapexec)
  install_tool_multi "netexec" "nxc" \
    "pip:netexec"

  # enum4linux — Kali-only; git clone fallback
  if ! tool_exists enum4linux; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "enum4linux (via pkg or git clone)"
    else
      echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}enum4linux${RESET} ... "
      local e4l_ok=false
      _pkg_install enum4linux &>/dev/null && tool_exists enum4linux && e4l_ok=true
      if [[ "$e4l_ok" != true ]]; then
        if _git_install "https://github.com/CiscoCXSecurity/enum4linux.git" "$HOME/.local/share/enum4linux"; then
          chmod +x "$HOME/.local/share/enum4linux/enum4linux.pl" 2>/dev/null || true
          _make_wrapper "enum4linux" "perl $HOME/.local/share/enum4linux/enum4linux.pl"
          tool_exists enum4linux && e4l_ok=true
        fi
      fi
      if [[ "$e4l_ok" == true ]]; then
        echo -e "${GREEN}done${RESET}"
        success "enum4linux installed"
        (( COUNT_INSTALLED++ )) || true
      else
        echo -e "${RED}failed${RESET}"
        FAILED_TOOLS+=("enum4linux")
        FAILED_REASONS["enum4linux"]="needs samba-tools; Kali/Parrot recommended"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "enum4linux — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # enum4linux-ng
  install_tool_multi "enum4linux-ng" "enum4linux-ng" \
    "pip:enum4linux-ng"

  # arp-scan
  install_tool_multi "arp-scan" "arp-scan" \
    "pkg:arp-scan"

  # nbtscan
  install_tool_multi "nbtscan" "nbtscan" \
    "pkg:nbtscan"

  # smbmap
  install_tool_multi "smbmap" "smbmap" \
    "pip:smbmap" \
    "pkg:smbmap"

  # autorecon
  install_tool_multi "autorecon" "autorecon" \
    "pip:autorecon"
}

# ─── Category: Web Application Security ──────────────────────────────────────
install_web() {
  section "🌐 Web Application Security Tools"

  # gobuster — go install or brew
  install_tool_multi "gobuster" "gobuster" \
    "go:github.com/OJ/gobuster/v3@latest" \
    "pkg:gobuster"

  # ffuf — go install or brew/apt
  install_tool_multi "ffuf" "ffuf" \
    "go:github.com/ffuf/ffuf/v2@latest" \
    "pkg:ffuf"

  # feroxbuster — cargo or brew
  if [[ "$OS" == "macos" ]]; then
    install_tool_multi "feroxbuster" "feroxbuster" \
      "pkg:feroxbuster" \
      "cargo:feroxbuster"
  else
    install_tool_multi "feroxbuster" "feroxbuster" \
      "cargo:feroxbuster" \
      "pkg:feroxbuster"
  fi

  # dirsearch — pip
  install_tool_multi "dirsearch" "dirsearch" \
    "pip:dirsearch" \
    "pkg:dirsearch"

  # dirb — apt/brew
  install_tool_multi "dirb" "dirb" \
    "pkg:dirb"

  # httpx — go install
  install_tool_multi "httpx" "httpx" \
    "go:github.com/projectdiscovery/httpx/cmd/httpx@latest"

  # katana — go install
  install_tool_multi "katana" "katana" \
    "go:github.com/projectdiscovery/katana/cmd/katana@latest"

  # hakrawler — go install
  install_tool_multi "hakrawler" "hakrawler" \
    "go:github.com/hakluke/hakrawler@latest"

  # gau (Get All URLs) — go install
  install_tool_multi "gau" "gau" \
    "go:github.com/lc/gau/v2/cmd/gau@latest"

  # waybackurls — go install
  install_tool_multi "waybackurls" "waybackurls" \
    "go:github.com/tomnomnom/waybackurls@latest"

  # nikto — apt/brew
  install_tool_multi "nikto" "nikto" \
    "pkg:nikto"

  # sqlmap — pip or apt
  install_tool_multi "sqlmap" "sqlmap" \
    "pip:sqlmap" \
    "pkg:sqlmap"

  # wpscan — gem
  install_tool_multi "wpscan" "wpscan" \
    "gem:wpscan" \
    "pkg:wpscan"

  # arjun — pip
  install_tool_multi "arjun" "arjun" \
    "pip:arjun"

  # paramspider — not on PyPI; git clone
  if ! tool_exists paramspider; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "paramspider (via git clone)"
    else
      echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}paramspider${RESET} via git clone ... "
      if _git_install "https://github.com/devanshbatham/ParamSpider.git" "$HOME/.local/share/paramspider"; then
        pip3 install --user --quiet "$HOME/.local/share/paramspider" 2>/dev/null || \
        pip3 install --user --quiet --break-system-packages "$HOME/.local/share/paramspider" 2>/dev/null || true
        if tool_exists paramspider; then
          echo -e "${GREEN}done${RESET}"
          success "paramspider installed via git clone"
          (( COUNT_INSTALLED++ )) || true
        else
          _make_wrapper "paramspider" "python3 -m paramspider"
          echo -e "${GREEN}done${RESET}"
          success "paramspider installed via git clone"
          (( COUNT_INSTALLED++ )) || true
        fi
      else
        echo -e "${RED}failed${RESET}"
        FAILED_TOOLS+=("paramspider")
        FAILED_REASONS["paramspider"]="git clone failed"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "paramspider — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # dalfox — go install
  install_tool_multi "dalfox" "dalfox" \
    "go:github.com/hahwul/dalfox/v2@latest"

  # wafw00f — pip
  install_tool_multi "wafw00f" "wafw00f" \
    "pip:wafw00f"

  # whatweb — apt/brew/gem
  install_tool_multi "whatweb" "whatweb" \
    "pkg:whatweb" \
    "gem:whatweb"

  # jwt-tool — pip (package is jwt_tool)
  install_tool_multi "jwt-tool" "jwt_tool" \
    "pip:jwt_tool"

  # wfuzz — pip or apt
  install_tool_multi "wfuzz" "wfuzz" \
    "pip:wfuzz" \
    "pkg:wfuzz"

  # commix — git clone (not reliably on PyPI)
  if ! tool_exists commix; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "commix (via pkg or git clone)"
    else
      echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}commix${RESET} ... "
      local cmx_ok=false
      _pkg_install commix &>/dev/null && tool_exists commix && cmx_ok=true
      if [[ "$cmx_ok" != true ]]; then
        if _git_install "https://github.com/commixproject/commix.git" "$HOME/.local/share/commix"; then
          _make_wrapper "commix" "python3 $HOME/.local/share/commix/commix.py"
          tool_exists commix && cmx_ok=true
        fi
      fi
      if [[ "$cmx_ok" == true ]]; then
        echo -e "${GREEN}done${RESET}"
        success "commix installed"
        (( COUNT_INSTALLED++ )) || true
      else
        echo -e "${RED}failed${RESET}"
        FAILED_TOOLS+=("commix")
        FAILED_REASONS["commix"]="git clone failed"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "commix — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # testssl.sh — git clone (not in Ubuntu repos)
  if ! tool_exists testssl.sh && ! tool_exists testssl; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "testssl.sh (via git clone)"
    else
      echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}testssl.sh${RESET} via git clone ... "
      if _git_install "https://github.com/drwetter/testssl.sh.git" "$HOME/.local/share/testssl.sh"; then
        ln -sf "$HOME/.local/share/testssl.sh/testssl.sh" "$HOME/.local/bin/testssl.sh"
        chmod +x "$HOME/.local/bin/testssl.sh"
        echo -e "${GREEN}done${RESET}"
        success "testssl.sh installed via git clone"
        (( COUNT_INSTALLED++ )) || true
      else
        echo -e "${RED}failed${RESET}"
        FAILED_TOOLS+=("testssl")
        FAILED_REASONS["testssl"]="git clone failed"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "testssl.sh — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # sslscan
  install_tool_multi "sslscan" "sslscan" \
    "pkg:sslscan"

  # sslyze
  install_tool_multi "sslyze" "sslyze" \
    "pip:sslyze"
}

# ─── Category: Authentication & Password ─────────────────────────────────────
install_auth() {
  section "🔐 Authentication & Password Security Tools"

  # hydra
  install_tool_multi "hydra" "hydra" \
    "pkg:hydra"

  # john the ripper
  install_tool_multi "john" "john" \
    "pkg:john"

  # hashcat
  install_tool_multi "hashcat" "hashcat" \
    "pkg:hashcat"

  # medusa
  install_tool_multi "medusa" "medusa" \
    "pkg:medusa"

  # patator
  install_tool_multi "patator" "patator" \
    "pip:patator"

  # evil-winrm
  install_tool_multi "evil-winrm" "evil-winrm" \
    "gem:evil-winrm"

  # hashid (replaces legacy hash-identifier)
  install_tool_multi "hashid" "hashid" \
    "pip:hashid" \
    "pkg:hashid"
}

# ─── Category: Binary Analysis & Reverse Engineering ─────────────────────────
install_binary() {
  section "🔬 Binary Analysis & Reverse Engineering Tools"

  # gdb
  install_tool_multi "gdb" "gdb" \
    "pkg:gdb"

  # radare2
  install_tool_multi "radare2" "radare2" \
    "pkg:radare2"

  # binwalk — try pkg first, pip fallback
  install_tool_multi "binwalk" "binwalk" \
    "pkg:binwalk" \
    "pip:binwalk"

  # ropgadget
  install_tool_multi "ropgadget" "ROPgadget" \
    "pip:ROPGadget"

  # ropper — pip
  install_tool_multi "ropper" "ropper" \
    "pip:ropper"

  # checksec — pip or apt
  install_tool_multi "checksec" "checksec" \
    "pip:checksec" \
    "pkg:checksec"

  # binutils (strings, objdump, readelf, xxd)
  if ! command -v strings &>/dev/null; then
    install_tool_multi "binutils (strings/objdump/readelf)" "strings" \
      "pkg:binutils"
  else
    skip "binutils (strings/objdump/readelf) — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # exiftool
  install_tool_multi "exiftool" "exiftool" \
    "pkg:libimage-exiftool-perl" \
    "pkg:exiftool"

  # volatility3 — pip
  install_tool_multi "volatility3" "vol" \
    "pip:volatility3"

  # foremost — apt/brew
  install_tool_multi "foremost" "foremost" \
    "pkg:foremost"

  # steghide — apt/brew
  install_tool_multi "steghide" "steghide" \
    "pkg:steghide"

  # one-gadget — gem
  install_tool_multi "one-gadget" "one_gadget" \
    "gem:one_gadget"

  # upx — apt/brew
  install_tool_multi "upx" "upx" \
    "pkg:upx"

  # pwntools and angr: note they are in requirements.txt
  info "pwntools & angr — managed via requirements.txt (pip3 install -r requirements.txt)"

  # GUI / manual-only tools
  skip_manual_install "Ghidra"       "https://ghidra-sre.org/"
  skip_manual_install "IDA Free"     "https://hex-rays.com/ida-free/"
  skip_manual_install "Binary Ninja" "https://binary.ninja/free/"
}

# ─── Category: Cloud & Container Security ────────────────────────────────────
install_cloud() {
  section "☁️  Cloud & Container Security Tools"

  # prowler — pip (heavy deps, needs Python 3.9+)
  FAIL_HINT="heavy Python deps; try: pip3 install prowler (needs Python 3.9+)"
  install_tool_multi "prowler" "prowler" \
    "pip:prowler"

  # trivy — brew or apt (Aqua Security repo on Linux)
  if [[ "$OS" == "macos" ]]; then
    install_tool_multi "trivy" "trivy" \
      "pkg:trivy"
  elif [[ "$PKG_MGR" == "apt" ]]; then
    if ! tool_exists trivy; then
      if [[ "$DRY_RUN" != true ]]; then
        info "Adding Aqua Security apt repo for trivy..."
        $SUDO apt-get install -y apt-transport-https &>/dev/null
        # Use curl (already bootstrapped) instead of wget; read codename from /etc/os-release
        local trivy_codename
        trivy_codename="$(. /etc/os-release && echo "${VERSION_CODENAME:-${UBUNTU_CODENAME:-focal}}")"
        curl -fsSL https://aquasecurity.github.io/trivy-repo/deb/public.key \
          | $SUDO gpg --dearmor -o /usr/share/keyrings/trivy.gpg &>/dev/null
        echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb ${trivy_codename} main" \
          | $SUDO tee /etc/apt/sources.list.d/trivy.list &>/dev/null
        $SUDO apt-get update -qq &>/dev/null
        _pkg_install "trivy"
        if tool_exists trivy; then
          success "trivy installed via apt"
          (( COUNT_INSTALLED++ )) || true
        else
          error "trivy apt install failed"
          FAILED_TOOLS+=("trivy")
          (( COUNT_FAILED++ )) || true
        fi
      else
        dry "trivy (via Aqua Security apt repo)"
      fi
    else
      skip "trivy — already installed"
      (( COUNT_ALREADY++ )) || true
    fi
  else
    install_tool_multi "trivy" "trivy" \
      "pkg:trivy"
  fi

  # kube-hunter — deprecated; use kube-bench instead
  if ! tool_exists kube-hunter; then
    info "kube-hunter — deprecated upstream; use kube-bench instead"
  else
    skip "kube-hunter — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # kube-bench — download binary
  if ! tool_exists kube-bench; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "kube-bench (via GitHub release binary → ~/.local/bin)"
    elif [[ "$OS" == "macos" ]]; then
      install_tool_multi "kube-bench" "kube-bench" \
        "pkg:kube-bench"
    else
      info "Downloading kube-bench binary to ~/.local/bin ..."
      mkdir -p "$HOME/.local/bin"
      local kb_arch
      kb_arch=$(uname -m); [[ "$kb_arch" == "x86_64" ]] && kb_arch="amd64" || kb_arch="arm64"
      local kb_ver
      kb_ver=$(curl -sL https://api.github.com/repos/aquasecurity/kube-bench/releases/latest \
               | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/')
      local kb_url="https://github.com/aquasecurity/kube-bench/releases/download/v${kb_ver}/kube-bench_${kb_ver}_linux_${kb_arch}.tar.gz"
      if curl -sL "$kb_url" | tar -xz -C "$HOME/.local/bin" kube-bench 2>/dev/null; then
        chmod +x "$HOME/.local/bin/kube-bench"
        success "kube-bench v${kb_ver} installed to ~/.local/bin"
        (( COUNT_INSTALLED++ )) || true
      else
        error "kube-bench download failed"
        FAILED_TOOLS+=("kube-bench")
        FAILED_REASONS["kube-bench"]="binary download failed"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "kube-bench — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # checkov
  FAIL_HINT="pip install requires many deps; try: pip3 install checkov"
  install_tool_multi "checkov" "checkov" \
    "pip:checkov"

  # aws-cli
  install_tool_multi "aws-cli" "aws" \
    "pip:awscli" \
    "pkg:awscli"

  # kubectl — direct binary download
  if ! tool_exists kubectl; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "kubectl (via pkg or binary download)"
    else
      echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}kubectl${RESET} ... "
      local kc_ok=false
      _pkg_install kubectl &>/dev/null && tool_exists kubectl && kc_ok=true
      if [[ "$kc_ok" != true ]]; then
        local kc_arch
        kc_arch=$(uname -m); [[ "$kc_arch" == "x86_64" ]] && kc_arch="amd64" || kc_arch="arm64"
        local kc_os; kc_os=$(uname -s | tr '[:upper:]' '[:lower:]')
        local kc_ver
        kc_ver=$(curl -sL https://dl.k8s.io/release/stable.txt 2>/dev/null)
        if [[ -n "$kc_ver" ]]; then
          mkdir -p "$HOME/.local/bin"
          if curl -sL "https://dl.k8s.io/release/${kc_ver}/bin/${kc_os}/${kc_arch}/kubectl" -o "$HOME/.local/bin/kubectl" 2>/dev/null; then
            chmod +x "$HOME/.local/bin/kubectl"
            tool_exists kubectl && kc_ok=true
          fi
        fi
      fi
      if [[ "$kc_ok" == true ]]; then
        echo -e "${GREEN}done${RESET}"
        success "kubectl installed"
        (( COUNT_INSTALLED++ )) || true
      else
        echo -e "${RED}failed${RESET}"
        FAILED_TOOLS+=("kubectl")
        FAILED_REASONS["kubectl"]="binary download failed"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "kubectl — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # helm — official install script
  if ! tool_exists helm; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "helm (via pkg or install script)"
    else
      echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}helm${RESET} ... "
      local helm_ok=false
      _pkg_install helm &>/dev/null && tool_exists helm && helm_ok=true
      if [[ "$helm_ok" != true ]]; then
        if curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | HELM_INSTALL_DIR="$HOME/.local/bin" USE_SUDO=false bash &>/dev/null; then
          tool_exists helm && helm_ok=true
        fi
      fi
      if [[ "$helm_ok" == true ]]; then
        echo -e "${GREEN}done${RESET}"
        success "helm installed"
        (( COUNT_INSTALLED++ )) || true
      else
        echo -e "${RED}failed${RESET}"
        FAILED_TOOLS+=("helm")
        FAILED_REASONS["helm"]="install script failed"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "helm — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # docker-bench-security note (scripts, not a binary)
  if ! tool_exists docker-bench-security; then
    info "docker-bench-security — clone from: https://github.com/docker/docker-bench-security"
    info "  Run with: sudo sh docker-bench-security.sh"
  fi
}

# ─── Category: CTF & Forensics ───────────────────────────────────────────────
install_ctf() {
  section "🏆 CTF & Digital Forensics Tools"

  # volatility3 — pip
  install_tool_multi "volatility3" "vol" \
    "pip:volatility3"

  # foremost
  install_tool_multi "foremost" "foremost" \
    "pkg:foremost"

  # steghide
  install_tool_multi "steghide" "steghide" \
    "pkg:steghide"

  # zsteg — gem
  install_tool_multi "zsteg" "zsteg" \
    "gem:zsteg"

  # outguess
  install_tool_multi "outguess" "outguess" \
    "pkg:outguess"

  # exiftool
  install_tool_multi "exiftool" "exiftool" \
    "pkg:libimage-exiftool-perl" \
    "pkg:exiftool"

  # testdisk / photorec
  install_tool_multi "testdisk/photorec" "testdisk" \
    "pkg:testdisk"

  # scalpel
  install_tool_multi "scalpel" "scalpel" \
    "pkg:scalpel"

  # bulk-extractor
  FAIL_HINT="not in Ubuntu 24.04 repos; build from source: github.com/simsong/bulk_extractor"
  install_tool_multi "bulk-extractor" "bulk_extractor" \
    "pkg:bulk-extractor"

  # autopsy note (GUI)
  skip_manual_install "Autopsy (GUI)" "https://www.autopsy.com/download/"

  # sleuthkit
  install_tool_multi "sleuthkit" "fls" \
    "pkg:sleuthkit"

  # john (often needed in CTF)
  install_tool_multi "john" "john" \
    "pkg:john"

  # hashcat
  install_tool_multi "hashcat" "hashcat" \
    "pkg:hashcat"

  # binwalk
  install_tool_multi "binwalk" "binwalk" \
    "pip:binwalk" \
    "pkg:binwalk"

  # pwntools — managed by requirements.txt
  info "pwntools — managed via requirements.txt"

  # stegsolve note (Java GUI jar)
  if ! tool_exists stegsolve; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "stegsolve (~/.local/bin/stegsolve)"
    else
      mkdir -p "$HOME/.local/bin"
      if curl -sL "https://github.com/eugenekolo/sec-tools/raw/master/stego/stegsolve/stegsolve/stegsolve.jar" \
          -o "$HOME/.local/bin/stegsolve.jar" 2>/dev/null; then
        # Create a wrapper script
        cat > "$HOME/.local/bin/stegsolve" <<'WRAPPER'
#!/usr/bin/env sh
java -jar "$HOME/.local/bin/stegsolve.jar" "$@"
WRAPPER
        chmod +x "$HOME/.local/bin/stegsolve"
        success "stegsolve jar installed to ~/.local/bin"
        (( COUNT_INSTALLED++ )) || true
      else
        error "stegsolve download failed — requires a JRE and manual download"
        FAILED_TOOLS+=("stegsolve")
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "stegsolve — already installed"
    (( COUNT_ALREADY++ )) || true
  fi
}

# ─── Category: OSINT ─────────────────────────────────────────────────────────
install_osint() {
  section "🕵️  OSINT & Intelligence Gathering Tools"

  # sherlock
  install_tool_multi "sherlock" "sherlock" \
    "pip:sherlock-project"

  # recon-ng — git clone (complex app, not a simple pip package)
  if ! tool_exists recon-ng; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "recon-ng (via git clone)"
    else
      echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}recon-ng${RESET} via git clone ... "
      if _git_install "https://github.com/lanmaster53/recon-ng.git" "$HOME/.local/share/recon-ng"; then
        pip3 install --user --quiet -r "$HOME/.local/share/recon-ng/REQUIREMENTS" 2>/dev/null || \
        pip3 install --user --quiet --break-system-packages -r "$HOME/.local/share/recon-ng/REQUIREMENTS" 2>/dev/null || true
        _make_wrapper "recon-ng" "python3 $HOME/.local/share/recon-ng/recon-ng"
        echo -e "${GREEN}done${RESET}"
        success "recon-ng installed via git clone"
        (( COUNT_INSTALLED++ )) || true
      else
        echo -e "${RED}failed${RESET}"
        FAILED_TOOLS+=("recon-ng")
        FAILED_REASONS["recon-ng"]="git clone failed"
        (( COUNT_FAILED++ )) || true
      fi
    fi
  else
    skip "recon-ng — already installed"
    (( COUNT_ALREADY++ )) || true
  fi

  # spiderfoot
  FAIL_HINT="complex web app; clone github.com/smicallef/spiderfoot"
  install_tool_multi "spiderfoot" "spiderfoot" \
    "pip:spiderfoot"

  # theharvester (may already be installed from network category)
  install_tool_multi "theharvester" "theHarvester" \
    "pip:theHarvester" \
    "pkg:theharvester"

  # social-analyzer
  install_tool_multi "social-analyzer" "social-analyzer" \
    "pip:social-analyzer"

  # trufflehog
  install_tool_multi "trufflehog" "trufflehog" \
    "go:github.com/trufflesecurity/trufflehog/v3@latest"

  # Maltego — GUI, skip
  skip_manual_install "Maltego (GUI)"  "https://www.maltego.com/downloads/"

  # Shodan CLI — needs API key
  info "shodan CLI — install with: pip3 install --user shodan  (requires API key at https://account.shodan.io/)"

  # Censys — needs API key
  info "censys CLI — install with: pip3 install --user censys  (requires API key at https://censys.io/)"
}

# ─── Category: Browser Agent ─────────────────────────────────────────────────
install_browser() {
  section "🌍 Browser Agent Dependencies (Chromium + ChromeDriver)"

  if [[ "$OS" == "macos" ]]; then
    # macOS: brew --cask
    if ! tool_exists chromium && ! tool_exists google-chrome; then
      if [[ "$DRY_RUN" == true ]]; then
        dry "chromium (brew install --cask chromium)"
      else
        echo -ne "  ${CYAN}↳${RESET} Installing ${BOLD}chromium${RESET} via brew cask ... "
        if brew install --cask chromium &>/dev/null; then
          echo -e "${GREEN}done${RESET}"
          success "chromium installed"
          (( COUNT_INSTALLED++ )) || true
        else
          echo -e "${YELLOW}skipped${RESET}"
          warn "Chromium cask install failed — install Google Chrome manually: https://www.google.com/chrome/"
          (( COUNT_SKIPPED++ )) || true
        fi
      fi
    else
      skip "chromium/chrome — already installed"
      (( COUNT_ALREADY++ )) || true
    fi

    install_tool_multi "chromedriver" "chromedriver" \
      "pkg:chromedriver"

  else
    # Linux
    if ! tool_exists chromium-browser && ! tool_exists chromium && ! tool_exists google-chrome; then
      install_tool_multi "chromium-browser" "chromium-browser" \
        "pkg:chromium-browser" \
        "pkg:chromium"
    else
      skip "chromium/chrome — already installed"
      (( COUNT_ALREADY++ )) || true
    fi

    install_tool_multi "chromium-chromedriver" "chromedriver" \
      "pkg:chromium-chromedriver" \
      "pkg:chromium-driver"
  fi
}

# ─── Summary ──────────────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BOLD}  📊 Installation Summary${RESET}"
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
  echo -e "  ${GREEN}✔  Installed:         $COUNT_INSTALLED${RESET}"
  echo -e "  ${DIM}~  Already present:   $COUNT_ALREADY${RESET}"
  echo -e "  ${MAGENTA}⊕  Manual required:   $COUNT_MANUAL${RESET}"
  echo -e "  ${RED}✘  Failed:            $COUNT_FAILED${RESET}"
  echo ""

  if [[ ${#MANUAL_TOOLS[@]} -gt 0 ]]; then
    echo -e "  ${MAGENTA}${BOLD}Manual Install Required:${RESET}"
    for t in "${MANUAL_TOOLS[@]}"; do
      echo -e "    ${MAGENTA}⊕${RESET} $t"
    done
    echo ""
  fi

  if [[ ${#FAILED_TOOLS[@]} -gt 0 ]]; then
    echo -e "  ${RED}${BOLD}Failed Tools:${RESET}"
    for t in "${FAILED_TOOLS[@]}"; do
      local reason="${FAILED_REASONS[$t]:-unknown}"
      printf "    ${RED}✘${RESET} %-20s ${DIM}— %s${RESET}\n" "$t" "$reason"
    done
    echo ""
  fi

  if [[ "$SHOW_LOG" == true ]]; then
    echo -e "  ${DIM}Full log: $LOG_FILE${RESET}"
    echo ""
    echo -e "  ${CYAN}${BOLD}── Install Log ──${RESET}"
    cat "$LOG_FILE" 2>/dev/null || true
    echo ""
  fi

  echo -e "  ${CYAN}${BOLD}Next Steps:${RESET}"
  echo -e "  1. Install Python dependencies:"
  echo -e "     ${DIM}pip3 install --user -r requirements.txt${RESET}"
  echo -e "  2. Ensure these are in your PATH (~/.bashrc or ~/.zshrc):"
  echo -e "     ${DIM}export PATH=\"\$PATH:\$HOME/.local/bin:\$HOME/go/bin:\$HOME/.cargo/bin\"${RESET}"
  echo -e "  3. Start the HexStrike server:"
  echo -e "     ${DIM}python3 hexstrike_server.py${RESET}"
  echo ""
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

# ─── Argument Parsing ─────────────────────────────────────────────────────────
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --show-log)
        SHOW_LOG=true
        shift
        ;;
      --only)
        if [[ -z "${2:-}" ]]; then
          error "--only requires a category name"
          echo "Valid categories: network, web, auth, binary, cloud, ctf, osint, browser"
          exit 1
        fi
        ONLY_CATEGORY="$2"
        shift 2
        ;;
      --list)
        print_list
        exit 0
        ;;
      --help|-h)
        print_help
        exit 0
        ;;
      *)
        error "Unknown argument: $1"
        echo "Run with --help for usage."
        exit 1
        ;;
    esac
  done

  # Validate --only value
  if [[ -n "$ONLY_CATEGORY" ]]; then
    case "$ONLY_CATEGORY" in
      network|web|auth|binary|cloud|ctf|osint|browser) ;;
      *)
        error "Unknown category: '$ONLY_CATEGORY'"
        echo "Valid categories: network, web, auth, binary, cloud, ctf, osint, browser"
        exit 1
        ;;
    esac
  fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
  parse_args "$@"
  print_banner

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${BLUE}${BOLD}DRY-RUN MODE — no packages will be installed${RESET}"
    echo ""
  fi

  # Initialize log
  echo "# HexStrike AI Tool Installer — $(date)" > "$LOG_FILE"
  log "DRY_RUN=$DRY_RUN ONLY_CATEGORY=${ONLY_CATEGORY:-all}"

  detect_os

  # Bootstrap curl + ca-certs BEFORE prerequisites so Go/Rust/Trivy downloaders can run
  if [[ "$DRY_RUN" != true ]]; then
    bootstrap_essentials
  fi

  check_prerequisites

  # Add Go/pip/gem/cargo bin dirs to PATH (critical: must run before tool installs)
  if [[ "$DRY_RUN" != true ]]; then
    setup_paths
  fi

  if [[ "$DRY_RUN" != true ]]; then
    check_paths
  fi

  # Refresh package lists once (Linux only, non-dry-run)
  if [[ "$DRY_RUN" != true && "$PKG_MGR" == "apt" ]]; then
    section "Updating Package Lists"
    echo -ne "  ${CYAN}↳${RESET} Running apt-get update ... "
    if $SUDO apt-get update -qq 2>/dev/null; then
      echo -e "${GREEN}done${RESET}"
    else
      echo -e "${YELLOW}skipped${RESET}"
      warn "apt-get update failed — some installs may fail"
    fi
  elif [[ "$DRY_RUN" != true && "$PKG_MGR" == "brew" ]]; then
    section "Updating Homebrew"
    echo -ne "  ${CYAN}↳${RESET} Running brew update ... "
    if brew update --quiet 2>/dev/null; then
      echo -e "${GREEN}done${RESET}"
    else
      echo -e "${YELLOW}skipped${RESET}"
    fi
  fi

  # Run selected categories
  if [[ -n "$ONLY_CATEGORY" ]]; then
    case "$ONLY_CATEGORY" in
      network) install_network ;;
      web)     install_web     ;;
      auth)    install_auth    ;;
      binary)  install_binary  ;;
      cloud)   install_cloud   ;;
      ctf)     install_ctf     ;;
      osint)   install_osint   ;;
      browser) install_browser ;;
    esac
  else
    install_network
    install_web
    install_auth
    install_binary
    install_cloud
    install_ctf
    install_osint
    install_browser
  fi

  print_summary
}

main "$@"
