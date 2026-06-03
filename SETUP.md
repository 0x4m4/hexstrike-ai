# HexStrike AI v6.0 — Setup & Usage Guide

This document covers the complete, verified setup process for HexStrike AI on macOS and Linux,
including platform-specific workarounds, Claude Desktop integration, and end-to-end verification.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Create a Virtual Environment](#2-create-a-virtual-environment)
  - [3. Install Python Dependencies](#3-install-python-dependencies)
    - [macOS: Required Workaround for `unicorn`](#macos-required-workaround-for-unicorn)
  - [4. Install External Security Tools](#4-install-external-security-tools)
- [Running the Server](#running-the-server)
  - [Foreground (development)](#foreground-development)
  - [Background (persistent)](#background-persistent)
  - [Keep Alive Across Reboots (macOS launchd)](#keep-alive-across-reboots-macos-launchd)
- [Running the MCP Client](#running-the-mcp-client)
- [Claude Desktop Integration](#claude-desktop-integration)
  - [1. Locate the Config File](#1-locate-the-config-file)
  - [2. Add the MCP Server Entry](#2-add-the-mcp-server-entry)
  - [3. Restart Claude Desktop](#3-restart-claude-desktop)
  - [4. Verify the Connection](#4-verify-the-connection)
- [Other AI Client Integrations](#other-ai-client-integrations)
- [Verifying the Installation](#verifying-the-installation)
- [Usage Examples](#usage-examples)
  - [Target Analysis](#target-analysis)
  - [Bug Bounty Recon Workflow](#bug-bounty-recon-workflow)
  - [AI Payload Generation](#ai-payload-generation)
  - [CTF Challenge Workflow](#ctf-challenge-workflow)
- [API Quick Reference](#api-quick-reference)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

HexStrike AI uses a two-process design:

```
AI Agent (Claude / GPT / Copilot)
        │  MCP protocol (stdio)
        ▼
hexstrike_mcp.py      ← MCP bridge — exposes tools to the AI agent
        │  HTTP REST (localhost:8888)
        ▼
hexstrike_server.py   ← Flask API server — wraps 150+ security tools
        │  subprocess
        ▼
External tools (nmap, sqlmap, nuclei, …)
```

| File | Role | Default Port |
|---|---|---|
| `hexstrike_server.py` | Flask REST API; wraps all security tools | 8888 |
| `hexstrike_mcp.py` | FastMCP bridge; exposes server tools as MCP tools | stdio |
| `hexstrike-ai-mcp.json` | Sample MCP config for AI clients | — |

---

## Prerequisites

### System requirements

| Requirement | Minimum | Notes |
|---|---|---|
| Python | 3.8+ | 3.10+ recommended |
| pip | 21+ | Upgrade with `pip install --upgrade pip` |
| RAM | 2 GB | 4 GB+ recommended when running angr/pwntools |
| Disk | 2 GB | For Python packages; security tools need additional space |

### macOS additional prerequisites

```bash
# Install Homebrew if not already present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Required system libraries
brew install cmake pkg-config
```

> **Why?** `angr` and `pwntools` both depend on the `unicorn` package, which must be compiled
> from source on some platforms and requires both `cmake` and `pkg-config`.

### Linux (Kali / Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv cmake pkg-config build-essential
```

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/0x4m4/hexstrike-ai.git
cd hexstrike-ai
```

### 2. Create a Virtual Environment

```bash
python3 -m venv hexstrike-env

# Activate (macOS / Linux)
source hexstrike-env/bin/activate

# Activate (Windows)
hexstrike-env\Scripts\activate
```

### 3. Install Python Dependencies

#### macOS: Required Workaround for `unicorn`

The `unicorn` package (required by both `pwntools` and `angr`) ships a `CMakeLists.txt`
incompatible with newer cmake versions. On macOS you must install a pre-built wheel first,
before installing the rest of the requirements:

```bash
# Step 1: install unicorn from a pre-built wheel (bypasses cmake build)
pip install --only-binary=:all: unicorn

# Step 2: install all remaining dependencies
pip install -r requirements.txt
```

#### Linux

No workaround needed:

```bash
pip install -r requirements.txt
```

#### Verify key imports

```bash
python3 -c "
import flask, requests, psutil, aiohttp, bs4, selenium, mitmproxy, angr
from mcp.server.fastmcp import FastMCP
import importlib.metadata
print('All imports OK')
print('flask:', importlib.metadata.version('flask'))
print('angr: ', angr.__version__)
"
```

Expected output:
```
All imports OK
flask: 3.1.x
angr:  9.2.x
```

### 4. Install External Security Tools

The Python packages above only cover the framework. The 150+ security tools (nmap, sqlmap,
nuclei, etc.) must be installed separately.

**On Kali Linux** (most tools are pre-installed):
```bash
sudo apt update && sudo apt install -y \
  nmap masscan rustscan gobuster feroxbuster ffuf nikto sqlmap \
  hydra john hashcat wpscan amass subfinder nuclei \
  radare2 binwalk gdb checksec volatility3 steghide exiftool foremost
```

**On macOS** (for development/testing only — most tools are Linux-targeted):
```bash
brew install nmap gobuster ffuf httpx
# Note: many tools (sqlmap, nuclei, etc.) still work via pip or go install
pip install sqlmap
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

> The server and all AI/intelligence/workflow features work without any external tools installed.
> Tool-specific endpoints (e.g. `/api/tools/nmap`) will return an error if the binary is missing,
> but the server itself remains healthy.

---

## Running the Server

### Foreground (development)

```bash
# Activate the venv first
source hexstrike-env/bin/activate

# Default: port 8888, debug off
python3 hexstrike_server.py

# Custom port
python3 hexstrike_server.py --port 9999

# Debug mode (verbose logging)
python3 hexstrike_server.py --debug
```

Expected startup output:
```
██╗  ██╗███████╗██╗  ██╗███████╗████████╗██████╗ ██╗██╗  ██╗███████╗
...
 * Running on http://0.0.0.0:8888
 * Press CTRL+C to quit
```

Flask is ready roughly 4–6 seconds after launch (process pool workers initialise first).

### Background (persistent)

The server must be started with `start_new_session=True` (or equivalent) so it survives
shell session teardown:

```bash
python3 -c "
import subprocess
log = open('/tmp/hexstrike_server.log', 'w')
p = subprocess.Popen(
    ['$(pwd)/hexstrike-env/bin/python3', 'hexstrike_server.py'],
    cwd='$(pwd)',
    stdout=log, stderr=log,
    start_new_session=True
)
print(f'Server PID: {p.pid}')
"
```

Check logs:
```bash
tail -f /tmp/hexstrike_server.log
```

Stop the server:
```bash
pkill -f hexstrike_server.py
```

### Keep Alive Across Reboots (macOS launchd)

Create `~/Library/LaunchAgents/com.hexstrike.server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.hexstrike.server</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/YOUR_USERNAME/hexstrike-ai/hexstrike-env/bin/python3</string>
    <string>/Users/YOUR_USERNAME/hexstrike-ai/hexstrike_server.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/YOUR_USERNAME/hexstrike-ai</string>
  <key>StandardOutPath</key>
  <string>/tmp/hexstrike_server.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/hexstrike_server.log</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.hexstrike.server.plist
```

---

## Running the MCP Client

The MCP client is a FastMCP bridge — it is not a long-running server you access directly.
Instead it is launched **by the AI client** (Claude Desktop, Cursor, etc.) via stdio.

You can test it manually:

```bash
source hexstrike-env/bin/activate

# Ensure the server is already running, then:
python3 hexstrike_mcp.py --server http://localhost:8888

# With debug logging
python3 hexstrike_mcp.py --server http://localhost:8888 --debug

# Custom timeout (seconds)
python3 hexstrike_mcp.py --server http://localhost:8888 --timeout 600
```

Expected output:
```
[🔥 HexStrike MCP] ... [INFO] 🚀 Starting HexStrike AI MCP Client v6.0
[🔥 HexStrike MCP] ... [INFO] 🔗 Connecting to: http://localhost:8888
[🔥 HexStrike MCP] ... [INFO] 🎯 Successfully connected to HexStrike AI API Server
[🔥 HexStrike MCP] ... [INFO] 🏥 Server health status: healthy
[🔥 HexStrike MCP] ... [INFO] 🚀 Starting HexStrike AI MCP server
[🔥 HexStrike MCP] ... [INFO] 🤖 Ready to serve AI agents
```

> If you see `⚠️ Not all essential tools are available` — this is normal on macOS or any
> machine without the full security tool suite installed. The MCP server still starts and
> all AI/workflow features remain functional.

---

## Claude Desktop Integration

### 1. Locate the Config File

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### 2. Add the MCP Server Entry

Edit the config file and add the `hexstrike-ai` entry inside `mcpServers`.
Use the **absolute path** to the venv's Python interpreter so Claude Desktop does not
depend on the shell's active environment:

```json
{
  "mcpServers": {
    "hexstrike-ai": {
      "command": "/ABSOLUTE/PATH/TO/hexstrike-ai/hexstrike-env/bin/python3",
      "args": [
        "/ABSOLUTE/PATH/TO/hexstrike-ai/hexstrike_mcp.py",
        "--server",
        "http://localhost:8888"
      ],
      "description": "HexStrike AI v6.0 - Advanced Cybersecurity Automation Platform"
    }
  }
}
```

**Example (macOS, installed in home directory):**

```json
{
  "mcpServers": {
    "hexstrike-ai": {
      "command": "/Users/username/hexstrike-ai/hexstrike-env/bin/python3",
      "args": [
        "/Users/username/hexstrike-ai/hexstrike_mcp.py",
        "--server",
        "http://localhost:8888"
      ],
      "description": "HexStrike AI v6.0 - Advanced Cybersecurity Automation Platform"
    }
  }
}
```

> **Important:** Use the venv Python (`hexstrike-env/bin/python3`), not the system `python3`.
> The system Python does not have the installed packages.

### 3. Restart Claude Desktop

```bash
# macOS
pkill -x "Claude" && open -a Claude
```

### 4. Verify the Connection

After Claude Desktop restarts, check the server log for health check requests:

```bash
grep "GET /health" /tmp/hexstrike_server.log
```

You should see lines like:
```
... "GET /health HTTP/1.1" 200 -
```

In Claude Desktop, a hammer icon (🔨) in the toolbar confirms MCP tools are loaded.

---

## Other AI Client Integrations

### VS Code Copilot / Roo Code / Cursor

Add to `.vscode/settings.json` or the equivalent MCP settings file:

```json
{
  "servers": {
    "hexstrike-ai": {
      "type": "stdio",
      "command": "/ABSOLUTE/PATH/TO/hexstrike-env/bin/python3",
      "args": [
        "/ABSOLUTE/PATH/TO/hexstrike_mcp.py",
        "--server",
        "http://localhost:8888"
      ]
    }
  }
}
```

### Any MCP-compatible Client

The `hexstrike-ai-mcp.json` file in the repo root is a ready-to-use template.
Edit it to replace the placeholder paths and IP address, then import it into your client.

---

## Verifying the Installation

Run these commands to confirm the full stack is working:

```bash
# 1. Server health
curl -s http://localhost:8888/health | python3 -m json.tool | grep -E '"status"|"version"|"total_tools'

# 2. Target intelligence analysis
curl -s -X POST http://localhost:8888/api/intelligence/analyze-target \
  -H "Content-Type: application/json" \
  -d '{"target": "example.com"}' | python3 -m json.tool | grep -E '"target_type"|"risk_level"'

# 3. AI payload generation
curl -s -X POST http://localhost:8888/api/ai/generate_payload \
  -H "Content-Type: application/json" \
  -d '{"attack_type": "xss", "complexity": "basic"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"ai_payload_generation\"][\"payload_count\"]} payloads generated')"

# 4. Bug bounty workflow
curl -s -X POST http://localhost:8888/api/bugbounty/reconnaissance-workflow \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Workflow ready: {d[\"success\"]}')"
```

All four should return results without errors, regardless of which external security tools
are installed.

---

## Usage Examples

### Prompting the AI Agent

Because LLMs apply ethical guardrails, always establish context before asking HexStrike
to test a target. A well-formed prompt looks like:

> *"I'm a security researcher. My company owns `target.example.com` and I have written
> authorisation to perform a penetration test. Please use the hexstrike-ai MCP tools to
> run a comprehensive assessment."*

The agent will then call the appropriate MCP tools automatically.

### Target Analysis

**Via API directly:**
```bash
curl -s -X POST http://localhost:8888/api/intelligence/analyze-target \
  -H "Content-Type: application/json" \
  -d '{
    "target": "target.example.com"
  }'
```

**Via Claude Desktop:**
> *"Analyse target.example.com using hexstrike and give me a risk profile."*

### Bug Bounty Recon Workflow

```bash
curl -s -X POST http://localhost:8888/api/bugbounty/comprehensive-assessment \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "target.example.com",
    "scope": ["*.target.example.com"],
    "priority_vulns": ["rce", "sqli", "xss", "idor", "ssrf"],
    "include_osint": true,
    "include_business_logic": true
  }'
```

### AI Payload Generation

```bash
# XSS payloads with WAF evasion
curl -s -X POST http://localhost:8888/api/ai/advanced-payload-generation \
  -H "Content-Type: application/json" \
  -d '{
    "attack_type": "xss",
    "target_context": "php",
    "evasion_level": "advanced"
  }'
```

### CTF Challenge Workflow

```bash
# Auto-generate a solving workflow for a binary exploitation challenge
curl -s -X POST http://localhost:8888/api/ctf/create-challenge-workflow \
  -H "Content-Type: application/json" \
  -d '{
    "name": "pwn_challenge",
    "category": "pwn",
    "difficulty": "medium",
    "points": 300,
    "target": "/path/to/binary"
  }'
```

---

## API Quick Reference

The server exposes 150+ REST endpoints. Key groups:

| Prefix | Description |
|---|---|
| `/health` | Server health and tool availability |
| `/api/command` | Execute arbitrary shell commands |
| `/api/intelligence/` | AI-driven target analysis and attack planning |
| `/api/bugbounty/` | Bug bounty hunting workflows |
| `/api/tools/<name>` | Individual security tool endpoints (nmap, sqlmap, nuclei, …) |
| `/api/ai/` | AI payload generation and testing |
| `/api/vuln-intel/` | CVE monitoring, exploit generation, attack chains |
| `/api/ctf/` | CTF challenge solving and analysis |
| `/api/processes/` | Live process management and dashboards |
| `/api/process/` | Advanced async execution and pool management |
| `/api/files/` | File creation, modification, deletion |
| `/api/python/` | Python script execution in isolated venvs |
| `/api/error-handling/` | Error classification and recovery stats |
| `/api/visual/` | Vulnerability cards and report generation |
| `/api/cache/` | Cache management |
| `/api/telemetry` | System telemetry |

Full endpoint details are in `hexstrike_server.py` (each route has a docstring).

---

## Troubleshooting

### `unicorn` fails to build (macOS)

**Symptom:** `error: [Errno 2] No such file or directory: 'cmake'`
or `typedef redefinition with different types ('Int128' …)`

**Fix:**
```bash
brew install cmake pkg-config
pip install --only-binary=:all: unicorn
pip install -r requirements.txt
```

### `fastmcp` / MCP import error

**Symptom:** `ModuleNotFoundError: No module named 'mcp'`

**Fix:** The `fastmcp` package provides the `mcp` namespace:
```bash
pip install fastmcp
```

### MCP client cannot connect to server

**Symptom:** `Connection refused` or `Failed to establish connection after 3 attempts`

**Fix:** Ensure the server is running before starting the MCP client:
```bash
curl http://localhost:8888/health   # must return JSON
python3 hexstrike_mcp.py --server http://localhost:8888
```

### Claude Desktop does not show the hammer (🔨) icon

**Checklist:**
1. The `command` path in `claude_desktop_config.json` must point to the **venv** Python,
   not the system Python.
2. The server must be running (`curl http://localhost:8888/health`).
3. Claude Desktop must be **fully restarted** after editing the config.
4. Check Claude Desktop logs: `~/Library/Logs/Claude/` (macOS).

### `Not all essential tools are available` warning

This is expected on macOS and any non-Kali system. The warning means security binaries
(nmap, sqlmap, etc.) are not in `PATH`. It does not prevent the server or MCP bridge from
starting. Tool-specific endpoints will return an error for missing binaries, but all
AI/intelligence/workflow endpoints continue to work.

### Port 8888 already in use

```bash
lsof -i :8888          # find the process
kill -9 <PID>          # stop it
python3 hexstrike_server.py --port 9999   # or use a different port
```

If using a non-default port, update the `--server` argument in both the MCP client
invocation and the Claude Desktop config to match:
```
--server http://localhost:9999
```
