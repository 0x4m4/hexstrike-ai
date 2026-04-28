#!/bin/bash

# HexStrike AI - Official Tools Verification Script (Based on Official README)
# Supports multiple Linux distributions with verified download links
# Version 3.5 - Complete coverage of all 70+ HexStrike AI tools

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
ORANGE='\033[0;33m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
echo "██╗  ██╗███████╗██╗  ██╗███████╗████████╗██████╗ ██╗██╗  ██╗███████╗"
echo "██║  ██║██╔════╝╚██╗██╔╝██╔════╝╚══██╔══╝██╔══██╗██║██║ ██╔╝██╔════╝"
echo "███████║█████╗   ╚███╔╝ ███████╗   ██║   ██████╔╝██║█████╔╝ █████╗  "
echo "██╔══██║██╔══╝   ██╔██╗ ╚════██║   ██║   ██╔══██╗██║██╔═██╗ ██╔══╝  "
echo "██║  ██║███████╗██╔╝ ██╗███████║   ██║   ██║  ██║██║██║  ██╗███████╗"
echo "╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚══════╝"
echo -e "${NC}"
echo -e "${WHITE}HexStrike AI - Official Security Tools Checker v3.5 by Cipherbytes9${NC}"
echo -e "${BLUE}🔗 Based on official HexStrike AI README - 70+ tools coverage${NC}"
echo -e "${ORANGE}📋 Comprehensive verification with working download links${NC}"
echo ""

# Check if curl is available for link validation
CURL_AVAILABLE=false
if command -v curl > /dev/null 2>&1; then
    CURL_AVAILABLE=true
fi

# Function to check if URL is accessible
check_url() {
    local url=$1
    if [ "$CURL_AVAILABLE" = true ]; then
        if curl --output /dev/null --silent --head --fail --max-time 10 "$url"; then
            return 0
        else
            return 1
        fi
    else
        return 0  # Assume working if curl not available
    fi
}

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
        PRETTY_NAME="$PRETTY_NAME"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
        PRETTY_NAME=$(cat /etc/redhat-release)
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
        PRETTY_NAME="Debian $(cat /etc/debian_version)"
    else
        DISTRO="unknown"
        PRETTY_NAME="Unknown Linux Distribution"
    fi
    
    # Detect architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) ARCH_TYPE="amd64" ;;
        aarch64|arm64) ARCH_TYPE="arm64" ;;
        armv7l) ARCH_TYPE="armv7" ;;
        i686|i386) ARCH_TYPE="i386" ;;
        *) ARCH_TYPE="amd64" ;;
    esac
    
    echo -e "${BLUE}🐧 Detected OS: ${CYAN}$PRETTY_NAME${NC}"
    echo -e "${BLUE}📋 Distribution: ${CYAN}$DISTRO${NC}"
    echo -e "${BLUE}🏗️  Architecture: ${CYAN}$ARCH ($ARCH_TYPE)${NC}"
    echo ""
}

# Get package manager and install commands based on distro
get_package_manager() {
    case $DISTRO in
        "ubuntu"|"debian"|"kali"|"parrot"|"mint")
            PKG_MANAGER="apt"
            INSTALL_CMD="sudo apt update && sudo apt install -y"
            UPDATE_CMD="sudo apt update"
            ;;
        "fedora"|"rhel"|"centos")
            if command -v dnf > /dev/null 2>&1; then
                PKG_MANAGER="dnf"
                INSTALL_CMD="sudo dnf install -y"
                UPDATE_CMD="sudo dnf update"
            else
                PKG_MANAGER="yum"
                INSTALL_CMD="sudo yum install -y"
                UPDATE_CMD="sudo yum update"
            fi
            ;;
        "arch"|"manjaro"|"endeavouros")
            PKG_MANAGER="pacman"
            INSTALL_CMD="sudo pacman -S"
            UPDATE_CMD="sudo pacman -Syu"
            ;;
        "opensuse"|"opensuse-leap"|"opensuse-tumbleweed")
            PKG_MANAGER="zypper"
            INSTALL_CMD="sudo zypper install -y"
            UPDATE_CMD="sudo zypper update"
            ;;
        "alpine")
            PKG_MANAGER="apk"
            INSTALL_CMD="sudo apk add"
            UPDATE_CMD="sudo apk update"
            ;;
        *)
            PKG_MANAGER="unknown"
            INSTALL_CMD="# Unknown package manager - manual installation required"
            UPDATE_CMD="# Unknown package manager"
            ;;
    esac
    
    echo -e "${BLUE}📦 Package Manager: ${CYAN}$PKG_MANAGER${NC}"
    echo ""
}

# Initialize counters
INSTALLED_COUNT=0
MISSING_COUNT=0
TOTAL_COUNT=0

# Arrays to store results
INSTALLED_TOOLS=()
MISSING_TOOLS=()

# Complete tool installation database based on HexStrike AI README
declare -A TOOL_INSTALL_INFO
init_complete_tool_database() {
    # 🔍 Network Reconnaissance & Scanning (from README)
    TOOL_INSTALL_INFO["nmap"]="pkg_manager|nmap|Advanced port scanning with custom NSE scripts"
    TOOL_INSTALL_INFO["amass"]="go_install|github.com/owasp-amass/amass/v4/cmd/amass|Comprehensive subdomain enumeration and OSINT"
    TOOL_INSTALL_INFO["subfinder"]="go_install|github.com/projectdiscovery/subfinder/v2/cmd/subfinder|Fast passive subdomain discovery"
    TOOL_INSTALL_INFO["nuclei"]="go_install|github.com/projectdiscovery/nuclei/v3/cmd/nuclei|Fast vulnerability scanner with 4000+ templates"
    TOOL_INSTALL_INFO["autorecon"]="pip_install|autorecon|Automated reconnaissance with 35+ parameters"
    TOOL_INSTALL_INFO["fierce"]="pip_install|fierce|DNS reconnaissance and zone transfer testing"
    TOOL_INSTALL_INFO["masscan"]="pkg_manager|masscan|High-speed Internet-scale port scanner"
    TOOL_INSTALL_INFO["rustscan"]="github_release|https://github.com/bee-san/RustScan/releases/download/2.3.0/rustscan_2.3.0_amd64.deb|Rust-based port scanner"
    TOOL_INSTALL_INFO["dnsenum"]="pkg_manager|dnsenum|DNS enumeration tool"
    TOOL_INSTALL_INFO["theharvester"]="pkg_manager|theharvester|Email/subdomain harvester"
    TOOL_INSTALL_INFO["responder"]="pkg_manager|responder|LLMNR/NBT-NS/MDNS poisoner"
    TOOL_INSTALL_INFO["netexec"]="pip_install|netexec|Network service exploitation tool"
    TOOL_INSTALL_INFO["enum4linux-ng"]="github_manual|https://github.com/cddmp/enum4linux-ng|Next-generation enum4linux"
    
    # 🌐 Web Application Security Testing (from README)
    TOOL_INSTALL_INFO["gobuster"]="pkg_manager|gobuster|Directory, file, and DNS enumeration"
    TOOL_INSTALL_INFO["ffuf"]="pkg_manager|ffuf|Fast web fuzzer with advanced filtering capabilities"
    TOOL_INSTALL_INFO["dirb"]="pkg_manager|dirb|Comprehensive web content scanner"
    TOOL_INSTALL_INFO["nikto"]="pkg_manager|nikto|Web server vulnerability scanner"
    TOOL_INSTALL_INFO["sqlmap"]="pkg_manager|sqlmap|Advanced automatic SQL injection testing"
    TOOL_INSTALL_INFO["wpscan"]="pkg_manager|wpscan|WordPress security scanner with vulnerability database"
    TOOL_INSTALL_INFO["burpsuite"]="manual_download|https://portswigger.net/burp/releases|Professional web security testing platform"
    TOOL_INSTALL_INFO["zaproxy"]="pkg_manager|zaproxy|OWASP ZAP web application security scanner"
    TOOL_INSTALL_INFO["arjun"]="pip_install|arjun|HTTP parameter discovery tool"
    TOOL_INSTALL_INFO["wafw00f"]="pkg_manager|wafw00f|Web application firewall fingerprinting"
    TOOL_INSTALL_INFO["feroxbuster"]="github_release|https://github.com/epi052/feroxbuster/releases/latest/download/x86_64-linux-feroxbuster.tar.gz|Fast content discovery tool"
    TOOL_INSTALL_INFO["dotdotpwn"]="github_manual|https://github.com/wireghoul/dotdotpwn|Directory traversal fuzzer"
    TOOL_INSTALL_INFO["xsser"]="pkg_manager|xsser|Cross-site scripting detection and exploitation"
    TOOL_INSTALL_INFO["wfuzz"]="pkg_manager|wfuzz|Web application fuzzer"
    TOOL_INSTALL_INFO["dirsearch"]="github_manual|https://github.com/maurosoria/dirsearch|Web path discovery tool"
    TOOL_INSTALL_INFO["httpx"]="go_install|github.com/projectdiscovery/httpx/cmd/httpx|HTTP toolkit"
    TOOL_INSTALL_INFO["katana"]="go_install|github.com/projectdiscovery/katana/cmd/katana|Web crawler"
    TOOL_INSTALL_INFO["paramspider"]="github_manual|https://github.com/devanshbatham/ParamSpider|Parameter mining tool"
    TOOL_INSTALL_INFO["dalfox"]="go_install|github.com/hahwul/dalfox/v2|XSS scanner and utility"
    
    # 🔐 Authentication & Password Security (from README)
    TOOL_INSTALL_INFO["hydra"]="pkg_manager|hydra|Network login cracker supporting 50+ protocols"
    TOOL_INSTALL_INFO["john"]="pkg_manager|john|Advanced password hash cracking"
    TOOL_INSTALL_INFO["hashcat"]="pkg_manager|hashcat|World's fastest password recovery tool"
    TOOL_INSTALL_INFO["medusa"]="pkg_manager|medusa|Speedy, parallel, modular login brute-forcer"
    TOOL_INSTALL_INFO["patator"]="pkg_manager|patator|Multi-purpose brute-forcer"
    TOOL_INSTALL_INFO["crackmapexec"]="pip_install|crackmapexec|Swiss army knife for pentesting networks"
    TOOL_INSTALL_INFO["evil-winrm"]="pkg_manager|evil-winrm|Windows Remote Management shell"
    TOOL_INSTALL_INFO["hash-identifier"]="pkg_manager|hash-identifier|Hash type identifier"
    TOOL_INSTALL_INFO["ophcrack"]="pkg_manager|ophcrack|Windows password cracker"
    
    # 🔬 Binary Analysis & Reverse Engineering (from README)
    TOOL_INSTALL_INFO["gdb"]="pkg_manager|gdb|GNU Debugger with Python scripting"
    TOOL_INSTALL_INFO["radare2"]="pkg_manager|radare2|Advanced reverse engineering framework"
    TOOL_INSTALL_INFO["binwalk"]="pkg_manager|binwalk|Firmware analysis and extraction tool"
    TOOL_INSTALL_INFO["ropgadget"]="pip_install|ropgadget|ROP/JOP gadget finder"
    TOOL_INSTALL_INFO["checksec"]="pkg_manager|checksec|Binary security property checker"
    TOOL_INSTALL_INFO["strings"]="pkg_manager|binutils|Extract printable strings from binaries"
    TOOL_INSTALL_INFO["objdump"]="pkg_manager|binutils|Display object file information"
    TOOL_INSTALL_INFO["ghidra"]="manual_download|https://github.com/NationalSecurityAgency/ghidra/releases|NSA's software reverse engineering suite"
    TOOL_INSTALL_INFO["xxd"]="pkg_manager|xxd|Hex dump utility"
    TOOL_INSTALL_INFO["volatility3"]="pip_install|volatility3|Memory forensics framework"
    TOOL_INSTALL_INFO["foremost"]="pkg_manager|foremost|File carving tool"
    TOOL_INSTALL_INFO["steghide"]="pkg_manager|steghide|Steganography tool"
    TOOL_INSTALL_INFO["exiftool"]="pkg_manager|libimage-exiftool-perl|Metadata reader/writer"
    
    # 🏆 Advanced CTF & Forensics Tools (from README)
    TOOL_INSTALL_INFO["volatility3"]="pip_install|volatility3|Advanced memory forensics framework"
    TOOL_INSTALL_INFO["foremost"]="pkg_manager|foremost|File carving and data recovery"
    TOOL_INSTALL_INFO["steghide"]="pkg_manager|steghide|Steganography detection and extraction"
    TOOL_INSTALL_INFO["exiftool"]="pkg_manager|libimage-exiftool-perl|Metadata reader/writer for various file formats"
    TOOL_INSTALL_INFO["hashpump"]="github_manual|https://github.com/cipherbytes9/HashPump|Hash length extension attack tool"
    TOOL_INSTALL_INFO["sleuthkit"]="pkg_manager|sleuthkit|Collection of command-line digital forensics tools"
    
    # ☁️ Cloud & Container Security (from README)
    TOOL_INSTALL_INFO["prowler"]="pip_install|prowler-cloud|AWS/Azure/GCP security assessment tool"
    TOOL_INSTALL_INFO["trivy"]="github_release|https://github.com/aquasecurity/trivy/releases/latest/download/trivy_0.50.1_Linux-64bit.tar.gz|Comprehensive vulnerability scanner for containers"
    TOOL_INSTALL_INFO["scout-suite"]="pip_install|scoutsuite|Multi-cloud security auditing tool"
    TOOL_INSTALL_INFO["kube-hunter"]="pip_install|kube-hunter|Kubernetes penetration testing tool"
    TOOL_INSTALL_INFO["kube-bench"]="github_release|https://github.com/aquasecurity/kube-bench/releases/latest/download/kube-bench_0.6.17_linux_amd64.tar.gz|CIS Kubernetes benchmark checker"
    TOOL_INSTALL_INFO["cloudsploit"]="github_manual|https://github.com/aquasecurity/cloudsploit|Cloud security scanning and monitoring"
    
    # 🔥 Bug Bounty & Reconnaissance Arsenal (from README)
    TOOL_INSTALL_INFO["hakrawler"]="go_install|github.com/hakluke/hakrawler|Fast web endpoint discovery and crawling"
    TOOL_INSTALL_INFO["httpx"]="go_install|github.com/projectdiscovery/httpx/cmd/httpx|Fast and multi-purpose HTTP toolkit"
    TOOL_INSTALL_INFO["paramspider"]="github_manual|https://github.com/devanshbatham/ParamSpider|Mining parameters from dark corners of web archives"
    TOOL_INSTALL_INFO["aquatone"]="github_release|https://github.com/michenriksen/aquatone/releases/latest/download/aquatone_linux_amd64_1.7.0.zip|Visual inspection of websites across hosts"
    TOOL_INSTALL_INFO["subjack"]="go_install|github.com/haccer/subjack|Subdomain takeover vulnerability checker"
    TOOL_INSTALL_INFO["dnsenum"]="pkg_manager|dnsenum|DNS enumeration script"
    
    # Additional tools mentioned in the server code but not explicitly in README categories
    TOOL_INSTALL_INFO["theharvester"]="pkg_manager|theharvester|Email/subdomain harvester"
    TOOL_INSTALL_INFO["responder"]="pkg_manager|responder|LLMNR/NBT-NS/MDNS poisoner"
    TOOL_INSTALL_INFO["netexec"]="pip_install|netexec|Network service exploitation tool"
    TOOL_INSTALL_INFO["enum4linux-ng"]="github_manual|https://github.com/cddmp/enum4linux-ng|Next-generation enum4linux"
    TOOL_INSTALL_INFO["dirsearch"]="github_manual|https://github.com/maurosoria/dirsearch|Web path discovery tool"
    TOOL_INSTALL_INFO["katana"]="go_install|github.com/projectdiscovery/katana/cmd/katana|Web crawler"
    TOOL_INSTALL_INFO["dalfox"]="go_install|github.com/hahwul/dalfox/v2|XSS scanner and utility"
    
    # Tools from the MCP code analysis
    TOOL_INSTALL_INFO["smbmap"]="pip_install|smbmap|SMB share enumeration tool"
    TOOL_INSTALL_INFO["msfvenom"]="pkg_manager|metasploit-framework|Metasploit payload generator"
    TOOL_INSTALL_INFO["msfconsole"]="pkg_manager|metasploit-framework|Metasploit console"
    TOOL_INSTALL_INFO["hash-identifier"]="pkg_manager|hash-identifier|Hash type identifier"
    TOOL_INSTALL_INFO["ophcrack"]="pkg_manager|ophcrack|Windows password cracker"
    TOOL_INSTALL_INFO["rustscan"]="github_release|https://github.com/bee-san/RustScan/releases/download/2.3.0/rustscan_2.3.0_amd64.deb|Ultra-fast port scanner"
}

# Function to get package name based on distribution
get_package_name() {
    local tool=$1
    
    case $DISTRO in
        "ubuntu"|"debian"|"kali"|"parrot"|"mint")
            case $tool in
                "theharvester") echo "theharvester" ;;
                "evil-winrm") echo "evil-winrm" ;;
                "hash-identifier") echo "hash-identifier" ;;
                "enum4linux-ng") echo "enum4linux-ng" ;;
                "httpx") echo "httpx-toolkit" ;;
                "volatility3") echo "volatility3" ;;
                "netexec") echo "netexec" ;;
                "exiftool") echo "libimage-exiftool-perl" ;;
                "zaproxy") echo "zaproxy" ;;
                "sleuthkit") echo "sleuthkit" ;;
                "metasploit-framework") echo "metasploit-framework" ;;
                "xxd") echo "xxd" ;;
                *) echo "$tool" ;;
            esac
            ;;
        "fedora"|"rhel"|"centos")
            case $tool in
                "theharvester") echo "theHarvester" ;;
                "evil-winrm") echo "rubygem-evil-winrm" ;;
                "enum4linux-ng") echo "enum4linux-ng" ;;
                "httpx") echo "httpx" ;;
                "volatility3") echo "python3-volatility3" ;;
                "exiftool") echo "perl-Image-ExifTool" ;;
                "zaproxy") echo "zaproxy" ;;
                "sleuthkit") echo "sleuthkit" ;;
                "metasploit-framework") echo "metasploit" ;;
                "xxd") echo "vim-common" ;;
                *) echo "$tool" ;;
            esac
            ;;
        "arch"|"manjaro"|"endeavouros")
            case $tool in
                "theharvester") echo "theharvester" ;;
                "evil-winrm") echo "evil-winrm" ;;
                "hash-identifier") echo "hash-identifier" ;;
                "enum4linux-ng") echo "enum4linux-ng" ;;
                "httpx") echo "httpx" ;;
                "volatility3") echo "volatility3" ;;
                "exiftool") echo "perl-image-exiftool" ;;
                "zaproxy") echo "zaproxy" ;;
                "sleuthkit") echo "sleuthkit" ;;
                "metasploit-framework") echo "metasploit" ;;
                "xxd") echo "xxd" ;;
                *) echo "$tool" ;;
            esac
            ;;
        *)
            echo "$tool"
            ;;
    esac
}

# Function to check if a command exists
check_tool() {
    local tool=$1
    local alt_check=$2
    
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    
    # Check primary command
    if command -v "$tool" > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}$tool${NC} - ${GREEN}INSTALLED${NC}"
        INSTALLED_TOOLS+=("$tool")
        INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
        return 0
    fi
    
    # Check alternative command if provided
    if [ -n "$alt_check" ] && command -v "$alt_check" > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}$tool${NC} (as $alt_check) - ${GREEN}INSTALLED${NC}"
        INSTALLED_TOOLS+=("$tool")
        INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
        return 0
    fi
    
    # Check if it's a Python package that might be installed
    if python3 -c "import $tool" > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}$tool${NC} (Python package) - ${GREEN}INSTALLED${NC}"
        INSTALLED_TOOLS+=("$tool")
        INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
        return 0
    fi
    
    # Check common installation locations
    local locations=(
        "/usr/bin/$tool"
        "/usr/local/bin/$tool"
        "/opt/$tool"
        "/home/$USER/tools/$tool"
        "/home/$USER/Desktop/$tool"
        "/usr/share/$tool"
        "/snap/bin/$tool"
        "/usr/local/share/$tool"
    )
    
    for location in "${locations[@]}"; do
        if [ -f "$location" ] || [ -d "$location" ]; then
            echo -e "✅ ${GREEN}$tool${NC} - ${GREEN}INSTALLED${NC} (found at $location)"
            INSTALLED_TOOLS+=("$tool")
            INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
            return 0
        fi
    done
    
    # Tool not found
    local package_name=$(get_package_name "$tool")
    echo -e "❌ ${RED}$tool${NC} - ${RED}NOT INSTALLED${NC} ${YELLOW}($PKG_MANAGER install $package_name)${NC}"
    MISSING_TOOLS+=("$tool:$package_name")
    MISSING_COUNT=$((MISSING_COUNT + 1))
    return 1
}

# Function to validate and generate installation commands
generate_verified_install_commands() {
    if [ $MISSING_COUNT -eq 0 ]; then
        return
    fi
    
    echo -e "${YELLOW}📦 HEXSTRIKE AI OFFICIAL INSTALLATION COMMANDS:${NC}"
    echo "================================================"
    
    local PKG_MANAGER_TOOLS=""
    local GO_TOOLS=""
    local PIP_TOOLS=""
    local GITHUB_RELEASES=""
    local MANUAL_INSTALLS=""
    local FAILED_VERIFICATIONS=""
    
    for missing in "${MISSING_TOOLS[@]}"; do
        local tool=$(echo "$missing" | cut -d':' -f1)
        local package=$(echo "$missing" | cut -d':' -f2)
        
        if [ -n "${TOOL_INSTALL_INFO[$tool]}" ]; then
            IFS='|' read -r install_type install_info description <<< "${TOOL_INSTALL_INFO[$tool]}"
            
            case $install_type in
                "pkg_manager")
                    PKG_MANAGER_TOOLS+=" $package"
                    ;;
                
                "go_install")
                    echo -e "${BLUE}🔍 Verifying Go package: $install_info${NC}"
                    if check_url "https://$install_info"; then
                        GO_TOOLS+="\n  go install -v $install_info@latest"
                        echo -e "  ✅ ${GREEN}Verified${NC}"
                    else
                        GO_TOOLS+="\n  go install -v $install_info@latest  # ⚠️  Could not verify"
                        echo -e "  ⚠️  ${YELLOW}Could not verify URL${NC}"
                    fi
                    ;;
                
                "pip_install")
                    PIP_TOOLS+="\n  pip3 install $install_info"
                    ;;
                
                "github_release")
                    echo -e "${BLUE}🔍 Verifying GitHub release: $install_info${NC}"
                    if check_url "$install_info"; then
                        GITHUB_RELEASES+="\n# $tool - $description\nwget $install_info\n"
                        echo -e "  ✅ ${GREEN}Download link verified${NC}"
                    else
                        # Try to find working alternative
                        local base_url=$(echo "$install_info" | sed 's|/releases/latest/download/.*|/releases|')
                        GITHUB_RELEASES+="\n# $tool - $description\n# ⚠️  Direct link failed, visit: $base_url\n"
                        FAILED_VERIFICATIONS+="\n❌ $tool: $install_info"
                        echo -e "  ❌ ${RED}Download link failed - check manually${NC}"
                    fi
                    ;;
                
                "github_manual")
                    echo -e "${BLUE}🔍 Verifying GitHub repo: $install_info${NC}"
                    if check_url "$install_info"; then
                        MANUAL_INSTALLS+="\n# $tool - $description\ngit clone $install_info\ncd $(basename $install_info)\n# Follow installation instructions in README\n"
                        echo -e "  ✅ ${GREEN}Repository verified${NC}"
                    else
                        MANUAL_INSTALLS+="\n# $tool - $description\n# ⚠️  Repository URL failed: $install_info\n"
                        FAILED_VERIFICATIONS+="\n❌ $tool: $install_info"
                        echo -e "  ❌ ${RED}Repository not accessible${NC}"
                    fi
                    ;;
                
                "manual_download")
                    echo -e "${BLUE}🔍 Verifying manual download: $install_info${NC}"
                    if check_url "$install_info"; then
                        MANUAL_INSTALLS+="\n# $tool - $description\n# Download from: $install_info\n# Extract and follow installation instructions\n"
                        echo -e "  ✅ ${GREEN}Download page verified${NC}"
                    else
                        MANUAL_INSTALLS+="\n# $tool - $description\n# ⚠️  Download page failed: $install_info\n"
                        FAILED_VERIFICATIONS+="\n❌ $tool: $install_info"
                        echo -e "  ❌ ${RED}Download page not accessible${NC}"
                    fi
                    ;;
            esac
        else
            PKG_MANAGER_TOOLS+=" $package"
        fi
    done
    
    echo ""
    
    # Display installation commands
    if [ -n "$PKG_MANAGER_TOOLS" ]; then
        echo -e "${CYAN}📦 Package Manager Installation ($PKG_MANAGER):${NC}"
        echo "$INSTALL_CMD$PKG_MANAGER_TOOLS"
        echo ""
    fi
    
    if [ -n "$PIP_TOOLS" ]; then
        echo -e "${CYAN}🐍 Python Package Installation:${NC}"
        echo -e "$PIP_TOOLS"
        echo ""
    fi
    
    if [ -n "$GO_TOOLS" ]; then
        echo -e "${CYAN}🐹 Go Package Installation (requires Go):${NC}"
        echo "# First install Go if not present:"
        case $DISTRO in
            "ubuntu"|"debian"|"kali"|"parrot"|"mint")
                echo "sudo apt install golang-go"
                ;;
            "fedora"|"rhel"|"centos")
                echo "sudo $PKG_MANAGER install go"
                ;;
            "arch"|"manjaro"|"endeavouros")
                echo "sudo pacman -S go"
                ;;
        esac
        echo -e "$GO_TOOLS"
        echo ""
    fi
    
    if [ -n "$GITHUB_RELEASES" ]; then
        echo -e "${CYAN}📁 GitHub Releases (Verified Links):${NC}"
        echo -e "$GITHUB_RELEASES"
        echo ""
    fi
    
    if [ -n "$MANUAL_INSTALLS" ]; then
        echo -e "${CYAN}🔧 Manual Installations:${NC}"
        echo -e "$MANUAL_INSTALLS"
        echo ""
    fi
    
    if [ -n "$FAILED_VERIFICATIONS" ]; then
        echo -e "${RED}⚠️  Failed Link Verifications:${NC}"
        echo -e "$FAILED_VERIFICATIONS"
        echo -e "\n${YELLOW}💡 For failed links, please check the official project repositories manually.${NC}"
        echo ""
    fi
    
    # HexStrike AI Official Installation Commands
    echo -e "${GREEN}🚀 HEXSTRIKE AI MEGA INSTALLATION COMMAND:${NC}"
    case $DISTRO in
        "ubuntu"|"debian"|"kali"|"parrot"|"mint")
            echo "# Network & Recon tools"
            echo "sudo apt update && sudo apt install -y nmap masscan amass fierce dnsenum theharvester responder"
            echo ""
            echo "# Web Application Security tools"
            echo "sudo apt install -y gobuster ffuf dirb nikto sqlmap wpscan wafw00f zaproxy xsser wfuzz"
            echo ""
            echo "# Password & Authentication tools"  
            echo "sudo apt install -y hydra john hashcat medusa patator evil-winrm hash-identifier ophcrack"
            echo ""
            echo "# Binary Analysis & Reverse Engineering tools"
            echo "sudo apt install -y gdb radare2 binwalk checksec binutils foremost steghide libimage-exiftool-perl sleuthkit xxd metasploit-framework"
            echo ""
            echo "# Python packages"
            echo "pip3 install autorecon ropgadget arjun crackmapexec netexec volatility3 prowler-cloud scoutsuite kube-hunter smbmap"
            echo ""
            echo "# Go packages (requires Go)"
            echo "go install github.com/owasp-amass/amass/v4/cmd/amass@latest"
            echo "go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
            echo "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
           echo "go install github.com/projectdiscovery/httpx/cmd/httpx@latest"
           echo "go install github.com/projectdiscovery/katana/cmd/katana@latest"
           echo "go install github.com/hahwul/dalfox/v2@latest"
           echo "go install github.com/hakluke/hakrawler@latest"
           echo "go install github.com/haccer/subjack@latest"
           ;;
       "fedora"|"rhel"|"centos")
           echo "# Network & Recon tools"
           echo "sudo $PKG_MANAGER install -y nmap masscan dnsenum theHarvester"
           echo ""
           echo "# Web Application Security tools"
           echo "sudo $PKG_MANAGER install -y gobuster ffuf dirb nikto sqlmap zaproxy wfuzz"
           echo ""
           echo "# Password & Authentication tools"
           echo "sudo $PKG_MANAGER install -y hydra john hashcat medusa patator rubygem-evil-winrm ophcrack"
           echo ""
           echo "# Binary Analysis & Reverse Engineering tools"
           echo "sudo $PKG_MANAGER install -y gdb radare2 binwalk binutils foremost steghide perl-Image-ExifTool sleuthkit vim-common"
           echo ""
           echo "# Python packages"
           echo "pip3 install autorecon ropgadget arjun crackmapexec netexec volatility3 prowler-cloud scoutsuite kube-hunter smbmap"
           ;;
       "arch"|"manjaro"|"endeavouros")
           echo "# Network & Recon tools"
           echo "sudo pacman -S nmap masscan dnsenum theharvester"
           echo ""
           echo "# Web Application Security tools"
           echo "sudo pacman -S gobuster ffuf dirb nikto sqlmap zaproxy wfuzz"
           echo ""
           echo "# Password & Authentication tools"
           echo "sudo pacman -S hydra john hashcat medusa patator evil-winrm hash-identifier ophcrack"
           echo ""
           echo "# Binary Analysis & Reverse Engineering tools"
           echo "sudo pacman -S gdb radare2 binwalk binutils foremost steghide perl-image-exiftool sleuthkit xxd metasploit"
           echo ""
           echo "# Python packages"
           echo "pip3 install autorecon ropgadget arjun crackmapexec netexec volatility3 prowler-cloud scoutsuite kube-hunter smbmap"
           ;;
   esac
   echo ""
}

# Main execution
echo -e "${ORANGE}🔍 Initializing complete HexStrike AI tool database...${NC}"
init_complete_tool_database

detect_distro
get_package_manager

if [ "$CURL_AVAILABLE" = false ]; then
   echo -e "${YELLOW}⚠️  curl not found. Link verification disabled. Install curl for full functionality.${NC}"
   echo ""
fi

echo -e "${MAGENTA}🔍 Network Reconnaissance & Scanning Tools${NC}"
echo "================================================"
check_tool "nmap"
check_tool "amass"
check_tool "subfinder"
check_tool "nuclei"
check_tool "autorecon"
check_tool "fierce"
check_tool "masscan"
check_tool "theharvester"
check_tool "responder"
check_tool "netexec" "nxc"
check_tool "enum4linux-ng"
check_tool "dnsenum"
check_tool "rustscan"
echo ""

echo -e "${MAGENTA}🌐 Web Application Security Testing Tools${NC}"
echo "================================================"
check_tool "gobuster"
check_tool "ffuf"
check_tool "dirb"
check_tool "nikto"
check_tool "sqlmap"
check_tool "wpscan"
check_tool "burpsuite"
check_tool "zaproxy" "zap"
check_tool "arjun"
check_tool "wafw00f"
check_tool "feroxbuster"
check_tool "dotdotpwn"
check_tool "xsser"
check_tool "wfuzz"
check_tool "dirsearch"
check_tool "katana"
check_tool "dalfox"
check_tool "httpx"
check_tool "paramspider"
echo ""

echo -e "${MAGENTA}🔐 Authentication & Password Security Tools${NC}"
echo "================================================"
check_tool "hydra"
check_tool "john"
check_tool "hashcat"
check_tool "medusa"
check_tool "patator"
check_tool "crackmapexec" "cme"
check_tool "evil-winrm"
check_tool "hash-identifier"
check_tool "ophcrack"
echo ""

echo -e "${MAGENTA}🔬 Binary Analysis & Reverse Engineering Tools${NC}"
echo "================================================"
check_tool "gdb"
check_tool "radare2" "r2"
check_tool "binwalk"
check_tool "ropgadget"
check_tool "checksec"
check_tool "strings"
check_tool "objdump"
check_tool "ghidra"
check_tool "xxd"
check_tool "msfvenom"
check_tool "msfconsole"
check_tool "smbmap"
echo ""

echo -e "${MAGENTA}🏆 Advanced CTF & Forensics Tools${NC}"
echo "================================================"
check_tool "volatility3" "vol3"
check_tool "foremost"
check_tool "steghide"
check_tool "exiftool"
check_tool "hashpump"
check_tool "autopsy"
check_tool "sleuthkit"
echo ""

echo -e "${MAGENTA}☁️ Cloud & Container Security Tools${NC}"
echo "================================================"
check_tool "prowler"
check_tool "trivy"
check_tool "scout-suite"
check_tool "kube-hunter"
check_tool "kube-bench"
check_tool "cloudsploit"
echo ""

echo -e "${MAGENTA}🔥 Bug Bounty & Reconnaissance Arsenal${NC}"
echo "================================================"
check_tool "hakrawler"
check_tool "httpx"
check_tool "paramspider"
check_tool "aquatone"
check_tool "subjack"
echo ""

# Summary
echo "================================================"
echo -e "${WHITE}📊 HEXSTRIKE AI INSTALLATION SUMMARY${NC}"
echo "================================================"
echo -e "✅ ${GREEN}Installed tools: $INSTALLED_COUNT/$TOTAL_COUNT${NC}"
echo -e "❌ ${RED}Missing tools: $MISSING_COUNT/$TOTAL_COUNT${NC}"

# HexStrike AI specific recommendations
echo ""
echo -e "${CYAN}📋 HEXSTRIKE AI OFFICIAL REQUIREMENTS:${NC}"
echo "================================================"

# Essential tools (based on README)
ESSENTIAL_TOOLS=("nmap" "nuclei" "gobuster" "ffuf" "sqlmap" "hydra" "gdb" "radare2")
ESSENTIAL_MISSING=0
ESSENTIAL_TOTAL=${#ESSENTIAL_TOOLS[@]}

echo -e "${YELLOW}🔥 Essential Tools Status:${NC}"
for tool in "${ESSENTIAL_TOOLS[@]}"; do
   if command -v "$tool" > /dev/null 2>&1; then
       echo -e "  ✅ ${GREEN}$tool${NC}"
   else
       echo -e "  ❌ ${RED}$tool${NC} - CRITICAL"
       ESSENTIAL_MISSING=$((ESSENTIAL_MISSING + 1))
   fi
done

echo ""
if [ $ESSENTIAL_MISSING -eq 0 ]; then
   echo -e "🎉 ${GREEN}All essential HexStrike AI tools are installed!${NC}"
else
   echo -e "⚠️  ${RED}$ESSENTIAL_MISSING/$ESSENTIAL_TOTAL essential tools missing. HexStrike AI functionality will be limited.${NC}"
fi

echo ""
echo -e "${BLUE}🤖 AI Agent Compatibility Status:${NC}"
if [ $MISSING_COUNT -eq 0 ]; then
   echo -e "✅ ${GREEN}Perfect! All 70+ tools ready for AI agent automation${NC}"
elif [ $MISSING_COUNT -le 10 ]; then
   echo -e "👍 ${YELLOW}Good! Most tools available - AI agents can perform comprehensive assessments${NC}"
elif [ $MISSING_COUNT -le 20 ]; then
   echo -e "⚠️  ${ORANGE}Moderate! Some limitations expected in AI agent capabilities${NC}"
else
   echo -e "❌ ${RED}Significant gaps! AI agents will have limited cybersecurity capabilities${NC}"
fi

if [ $MISSING_COUNT -gt 0 ]; then
   echo ""
   generate_verified_install_commands
fi

# Performance indicator with HexStrike AI context
PERCENTAGE=$(( (INSTALLED_COUNT * 100) / TOTAL_COUNT ))
echo ""
echo -e "${WHITE}📈 HEXSTRIKE AI READINESS SCORE: $PERCENTAGE%${NC}"

if [ $PERCENTAGE -ge 90 ]; then
   echo -e "🔥 ${GREEN}ELITE SETUP! Your AI agents are ready for advanced autonomous pentesting!${NC}"
   echo -e "${GREEN}✅ Full HexStrike AI capabilities unlocked${NC}"
elif [ $PERCENTAGE -ge 80 ]; then
   echo -e "🚀 ${GREEN}EXCELLENT! AI agents can perform comprehensive security assessments${NC}"
   echo -e "${GREEN}✅ Most HexStrike AI features available${NC}"
elif [ $PERCENTAGE -ge 70 ]; then
   echo -e "👍 ${YELLOW}GOOD! AI agents have solid cybersecurity capabilities${NC}"
   echo -e "${YELLOW}⚠️  Some advanced features may be limited${NC}"
elif [ $PERCENTAGE -ge 50 ]; then
   echo -e "⚠️  ${ORANGE}MODERATE! Basic AI agent security testing possible${NC}"
   echo -e "${ORANGE}❌ Advanced HexStrike AI features unavailable${NC}"
else
   echo -e "❌ ${RED}INSUFFICIENT! Major limitations in AI agent capabilities${NC}"
   echo -e "${RED}🔧 Install more tools for meaningful HexStrike AI functionality${NC}"
fi

echo ""
echo -e "${BLUE}💡 NEXT STEPS FOR HEXSTRIKE AI:${NC}"
echo "1. Install missing tools using the commands above"
echo "2. Clone HexStrike AI: git clone https://github.com/0x4m4/hexstrike-ai.git"
echo "3. Install Python dependencies: pip3 install -r requirements.txt"
echo "4. Start the server: python3 hexstrike_server.py"
echo "5. Configure your AI agent with the MCP client"
echo ""
echo -e "${CYAN}🌐 Official HexStrike AI Resources:${NC}"
echo "📖 Documentation: https://github.com/0x4m4/hexstrike-ai/blob/master/README.md"
echo "🔗 Project Page: https://www.hexstrike.com"
echo "👨‍💻 Author: 0x4m4 (https://www.0x4m4.com)"
echo ""
echo -e "${WHITE}🤖 Ready to empower your AI agents with autonomous cybersecurity capabilities!${NC}"
echo ""
