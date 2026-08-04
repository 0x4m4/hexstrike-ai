#!/bin/bash

# HexStrike AI macOS Setup Script
# This script installs missing security tools and sets up the environment.

echo "🔥 HexStrike AI - macOS Setup"
echo "=============================="

# Ensure Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install it first: https://brew.sh/"
    exit 1
fi

echo "[*] Updating Homebrew..."
brew update

echo "[*] Installing core security tools..."
brew install nmap gobuster nuclei sqlmap hydra john-jumbo aircrack-ng amass binwalk bulk-extractor checkov dirb dirsearch dnsenum exiftool feroxbuster ffuf fierce foremost gdb hashcat httpx masscan medusa nikto prowler radare2 subfinder trivy wafw00f wfuzz wpscan sleuthkit exploitdb testdisk samba httpie

echo "[*] Installing Python-based tools..."
pip3 install arjun netexec pwntools responder enum4linux-ng sherlock-project theharvester scoutsuite trufflehog shodan censys

echo "[*] Installing specialized tools via taps..."
brew install tomnomnom/tap/anew
brew install tomnomnom/tap/waybackurls
brew install projectdiscovery/tap/katana

echo "[*] Installing GUI/Heavy tools (Casks)..."
brew install --cask wireshark burp-suite-free-edition metasploit postman owasp-zap

echo "[*] Setting up local wordlists..."
mkdir -p wordlists/dirb
mkdir -p wordlists/dirbuster
mkdir -p wordlists/dirsearch
mkdir -p wordlists/x8
mkdir -p wordlists/api

# Download basic common wordlists
echo "[*] Downloading basic wordlists..."
curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt -o wordlists/dirb/common.txt
curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-medium.txt -o wordlists/dirbuster/directory-list-2.3-medium.txt
curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Leaked-Databases/rockyou-20.txt -o wordlists/rockyou.txt # Using a smaller version for now
curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api/api-endpoints.txt -o wordlists/api/api-endpoints.txt

echo "[*] Setup complete! You can now start the server with: python3 hexstrike_server.py"
