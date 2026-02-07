#!/bin/bash

# ============================================================================
# HEXSTRIKE AI - IMMORTAL STABILIZIER (v1.0)
# ============================================================================
# This script ensures the HexStrike AI environment is ALWAYS functional.
# It handles Python version stabilization, patch application, and service recovery.

PROJECT_DIR="/Users/thealchemist/hexstrike-ai/hexstrike-ai"
VENV_PATH="$PROJECT_DIR/hexstrike-env"
PYTHON_STABLE="3.11.13"

echo "[*] Initializing Dominance Stabilization..."

# 1. Ensure Python Version Stability
if ! command -v pyenv &> /dev/null; then
    echo "[!] pyenv not found. Installing via brew..."
    brew install pyenv
fi

if ! pyenv versions | grep -q "$PYTHON_STABLE"; then
    echo "[*] Installing stable Python $PYTHON_STABLE..."
    pyenv install "$PYTHON_STABLE"
fi

# 2. Verify/Recreate Virtual Environment
if [ ! -d "$VENV_PATH" ]; then
    echo "[*] Recreating missing environment..."
    ~/.pyenv/versions/$PYTHON_STABLE/bin/python -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"

# 3. Apply Critical Patches (Bcrypt/Unicorn Conflict)
echo "[*] Auditing dependency integrity..."
pip install --upgrade pip &> /dev/null
pip install bcrypt==4.0.1 unicorn==2.1.1 pwntools angr fastmcp flask requests psutil &> /dev/null

# 4. Verify Server Health
echo "[*] Auditing server reachability..."
if ! curl -s http://127.0.0.1:8888/health | grep -q "healthy"; then
    echo "[!] Server not responding. Restarting LaunchAgent..."
    launchctl unload ~/Library/LaunchAgents/com.hexstrike.server.plist 2>/dev/null
    launchctl load ~/Library/LaunchAgents/com.hexstrike.server.plist
fi

echo "[+] System STABILIZED. Dominance sustained."
