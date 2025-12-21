#!/bin/bash
# HexStrike AI MCP Setup Script for WSL
# Configures Claude Code in WSL to connect to HexStrike server running in a Kali VM
# See WSL_SETUP.md for full documentation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_SCRIPT="$SCRIPT_DIR/hexstrike_mcp.py"

echo "=========================================="
echo "  HexStrike AI MCP - WSL Setup Script"
echo "=========================================="
echo ""

# Step 1: Check if MCP script exists
if [[ ! -f "$MCP_SCRIPT" ]]; then
    echo "ERROR: hexstrike_mcp.py not found at $MCP_SCRIPT"
    exit 1
fi
echo "[OK] Found hexstrike_mcp.py"

# Step 2: Install Python dependencies
echo ""
echo "[*] Installing Python dependencies..."
pip3 install --quiet requests fastmcp flask psutil beautifulsoup4 aiohttp 2>/dev/null || {
    echo "[!] pip3 install failed, trying with --user flag..."
    pip3 install --user requests fastmcp flask psutil beautifulsoup4 aiohttp
}
echo "[OK] Python dependencies installed"

# Step 3: Test imports
echo ""
echo "[*] Testing Python imports..."
python3 -c "import requests; from mcp.server.fastmcp import FastMCP; print('[OK] All imports successful')" || {
    echo "ERROR: Python imports failed. Check installation."
    exit 1
}

# Step 4: Detect Windows host IP
echo ""
echo "[*] Detecting Windows host IP..."
WINDOWS_HOST_IP=$(ip route show default | awk '{print $3}')

if [[ -z "$WINDOWS_HOST_IP" ]]; then
    echo "ERROR: Could not detect Windows host IP"
    exit 1
fi
echo "[OK] Windows host IP: $WINDOWS_HOST_IP"

# Step 5: Test connectivity
echo ""
echo "[*] Testing connection to HexStrike server at $WINDOWS_HOST_IP:8888..."
if curl -s --connect-timeout 5 "http://$WINDOWS_HOST_IP:8888/health" > /dev/null 2>&1; then
    echo "[OK] HexStrike server is reachable!"
else
    echo ""
    echo "=========================================="
    echo "  WINDOWS CONFIGURATION REQUIRED"
    echo "=========================================="
    echo ""
    echo "The HexStrike server is not reachable from WSL."
    echo "Run these commands in PowerShell (as Administrator):"
    echo ""
    echo "  # Add firewall rule"
    echo "  New-NetFirewallRule -DisplayName 'WSL to HexStrike' -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow"
    echo ""
    echo "  # Create port proxy"
    echo "  netsh interface portproxy add v4tov4 listenport=8888 listenaddress=$WINDOWS_HOST_IP connectport=8888 connectaddress=127.0.0.1"
    echo ""
    echo "After running those commands, re-run this script."
    echo ""

    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

# Step 6: Configure Claude Code MCP
echo ""
echo "[*] Configuring Claude Code MCP..."

CLAUDE_CONFIG="$HOME/.claude.json"

if [[ ! -f "$CLAUDE_CONFIG" ]]; then
    echo "ERROR: Claude Code config not found at $CLAUDE_CONFIG"
    echo "Make sure Claude Code is installed and has been run at least once."
    exit 1
fi

# Check if hexstrike-ai already configured
if grep -q "hexstrike-ai" "$CLAUDE_CONFIG" 2>/dev/null; then
    echo "[!] hexstrike-ai already exists in config"
    echo "[*] Updating server URL to use $WINDOWS_HOST_IP..."

    # Use sed to update the URL (handles both localhost and any IP)
    sed -i "s|http://[^\"]*:8888|http://$WINDOWS_HOST_IP:8888|g" "$CLAUDE_CONFIG"
    echo "[OK] Updated MCP config"
else
    echo "[*] Adding hexstrike-ai to Claude Code..."

    # Use claude mcp add command
    claude mcp add hexstrike-ai -s user -- python3 "$MCP_SCRIPT" --server "http://$WINDOWS_HOST_IP:8888" 2>/dev/null || {
        echo "[!] Could not use 'claude mcp add' command"
        echo ""
        echo "Please manually add to ~/.claude.json mcpServers:"
        echo ""
        echo '  "hexstrike-ai": {'
        echo '    "type": "stdio",'
        echo '    "command": "python3",'
        echo '    "args": ['
        echo "      \"$MCP_SCRIPT\","
        echo '      "--server",'
        echo "      \"http://$WINDOWS_HOST_IP:8888\""
        echo '    ],'
        echo '    "env": {}'
        echo '  }'
        echo ""
    }
fi

# Step 7: Final verification
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  - MCP Script: $MCP_SCRIPT"
echo "  - Server URL: http://$WINDOWS_HOST_IP:8888"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code"
echo "  2. Run /mcp to verify hexstrike-ai is connected"
echo "  3. HexStrike tools will be available as mcp__hexstrike-ai__*"
echo ""

# Optional: Test the MCP script directly
read -p "Test MCP script now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "[*] Testing MCP script (Ctrl+C to stop)..."
    python3 "$MCP_SCRIPT" --server "http://$WINDOWS_HOST_IP:8888" --help
fi
