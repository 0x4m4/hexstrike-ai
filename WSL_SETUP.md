# HexStrike AI MCP Setup for WSL

This guide covers setting up the HexStrike AI MCP client in **WSL2** to connect to a **HexStrike server running in a Kali Linux VM** on the same Windows machine.

**Typical Setup:** You have Claude Code running in WSL on Windows, and HexStrike server running in a Kali VM (VMware/VirtualBox/Hyper-V) also on the same Windows machine. This guide bridges that connection.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Windows Host Machine                                             │
│                                                                  │
│  ┌────────────────────────┐                                      │
│  │ Kali Linux VM          │                                      │
│  │ (VMware/VBox/Hyper-V)  │                                      │
│  │                        │     ┌──────────────────────────┐     │
│  │  hexstrike_server      │────►│ VM Port Forward to       │     │
│  │  listening on :8888    │     │ Windows 127.0.0.1:8888   │     │
│  └────────────────────────┘     └──────────────────────────┘     │
│                                              │                    │
│                                              │ netsh portproxy    │
│                                              ▼                    │
│                              ┌──────────────────────────────┐    │
│                              │ WSL Gateway: 172.x.x.1:8888  │    │
│                              └──────────────────────────────┘    │
│                                              │                    │
│  ┌───────────────────────────────────────────┼───────────────┐   │
│  │ WSL2 (Ubuntu/Debian)                      ▼               │   │
│  │  ┌─────────────────────────────────────────────────────┐  │   │
│  │  │ Claude Code CLI                                     │  │   │
│  │  │  └── hexstrike_mcp.py → http://172.x.x.1:8888      │  │   │
│  │  └─────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**The Problem:** WSL2 can't reach `localhost` on Windows directly, and definitely can't reach your Kali VM. We solve this by port-forwarding through Windows as a bridge.

## Prerequisites

- WSL2 installed and running (Ubuntu, Debian, etc.)
- Claude Code CLI installed in WSL
- **Kali Linux VM** running with HexStrike server started
- VM port forwarding configured (VM's port 8888 → Windows 127.0.0.1:8888)
- Python 3.8+ in WSL

## Quick Setup

Run the setup script:

```bash
cd /path/to/hexstrike-ai
./wsl-setup.sh
```

## Manual Setup

### Step 1: Install Python Dependencies (WSL)

```bash
# Install required packages to system Python
pip3 install requests fastmcp flask psutil beautifulsoup4 aiohttp
```

### Step 2: Get Windows Host IP from WSL

WSL's `localhost` doesn't route to Windows. You need the Windows host IP:

```bash
# Get the Windows host IP (usually the default gateway)
ip route show default | awk '{print $3}'
```

This typically returns something like `172.17.224.1` or `172.x.x.1`.

### Step 3: Configure Windows Networking (PowerShell as Admin)

Run these commands in PowerShell with Administrator privileges:

```powershell
# Get the WSL gateway IP (run this first to find your specific IP)
wsl -e ip route show default

# Add firewall rule to allow WSL traffic
New-NetFirewallRule -DisplayName "WSL to HexStrike" -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow

# Create port proxy from WSL interface to localhost
# Replace 172.17.224.1 with YOUR gateway IP from the command above
netsh interface portproxy add v4tov4 listenport=8888 listenaddress=172.17.224.1 connectport=8888 connectaddress=127.0.0.1
```

To verify the port proxy:
```powershell
netsh interface portproxy show all
```

To remove later if needed:
```powershell
netsh interface portproxy delete v4tov4 listenport=8888 listenaddress=172.17.224.1
```

### Step 4: Test Connectivity (WSL)

```bash
# Replace with your Windows host IP
curl http://172.17.224.1:8888/health
```

You should see a JSON response with server status.

### Step 5: Add MCP to Claude Code

```bash
# Replace IP with your Windows host IP
claude mcp add hexstrike-ai -s user -- python3 /path/to/hexstrike-ai/hexstrike_mcp.py --server http://172.17.224.1:8888
```

Or manually edit `~/.claude.json` and add to `mcpServers`:

```json
{
  "mcpServers": {
    "hexstrike-ai": {
      "type": "stdio",
      "command": "python3",
      "args": [
        "/path/to/hexstrike-ai/hexstrike_mcp.py",
        "--server",
        "http://172.17.224.1:8888"
      ],
      "env": {}
    }
  }
}
```

### Step 6: Restart Claude Code

Exit and restart Claude Code. Check `/mcp` to verify hexstrike-ai is connected.

## Troubleshooting

### Connection Refused (exit code 7)
- Windows Firewall is blocking the connection
- Run the firewall rule command in Step 3

### Connection Reset (exit code 56)
- Port proxy not configured
- Run the netsh portproxy command in Step 3

### Module Not Found Errors
- Missing Python dependencies
- Run `pip3 install requests fastmcp` in WSL

### MCP Not Showing in Claude Code
- Config syntax error in ~/.claude.json
- Restart Claude Code after config changes

### Finding Your WSL Gateway IP
The gateway IP can change after WSL restarts. To make it persistent, consider:

1. **Check on each session:**
   ```bash
   ip route show default | awk '{print $3}'
   ```

2. **Or use mirrored networking (WSL 2.0+):**
   Add to `%USERPROFILE%\.wslconfig`:
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
   Then `wsl --shutdown` and restart. With mirrored mode, `localhost` works directly.

## Verification

Once set up, you should see hexstrike-ai tools available in Claude Code:
- Run `/mcp` to see server status
- Tools will be prefixed with `mcp__hexstrike-ai__`
