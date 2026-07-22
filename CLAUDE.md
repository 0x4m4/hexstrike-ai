# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

HexStrike AI (v6.0) is an MCP-driven security automation platform that exposes 150+ external security tools (nmap, nuclei, ffuf, gdb, prowler, etc.) to AI agents. Upstream: `https://github.com/0x4m4/hexstrike-ai`.

It is **two cooperating processes**, not one app:

- **`hexstrike_server.py`** (~17k lines) — a Flask HTTP API on `0.0.0.0:8888`. This is where everything actually happens: 156 `@app.route` endpoints, the decision/workflow/exploit engines, and all real tool execution via `subprocess`.
- **`hexstrike_mcp.py`** (~5k lines) — a thin FastMCP client with 151 `@mcp.tool()` wrappers. Each tool just calls `HexStrikeClient.safe_get/safe_post` against the Flask server's HTTP API. This is the process an AI client (Claude Desktop/Code, Cursor, Copilot) actually connects to.

**Consequence that trips people up:** the MCP tools are inert unless the Flask server is running. `HexStrikeClient` pings `/health` on startup; if the server is down every tool returns a connection error. Debug tool behavior against the HTTP API first, not the MCP layer.

## Running

```bash
# Start the backend Flask server (must be running for any MCP tool to work)
python3 hexstrike_server.py                 # default port 8888
python3 hexstrike_server.py --port 8888 --debug
# Port also settable via env: HEXSTRIKE_PORT=9000

# Verify it's up
curl http://localhost:8888/health           # returns tools_status + telemetry

# Install Python deps (see header of requirements.txt)
python3 -m venv hexstrike-env && source hexstrike-env/bin/activate
python3 -m pip install -r requirements.txt
```

The MCP client is launched by the AI client per `hexstrike-ai-mcp.json`, which runs
`python3 hexstrike_mcp.py --server http://127.0.0.1:8888`. That config points at a specific
interpreter (`hexstrike-dev/bin/python3` on this machine); several venvs exist here
(`venv`, `hexstrike-env`, `hexstrike_env`, `hexstrike-dev`) — all have flask+fastmcp.

There is **no test suite / linter config** in this repo. "Verification" means: start the server and hit `/health`, or call the `server_health` MCP tool. The many `if __name__ == "__main__":` blocks inside `hexstrike_server.py` are per-class self-test demos, not a runner.

## AI-client integration config

The AI client (Claude Desktop/Code, Cursor, VS Code Copilot) launches the **MCP client** process itself — you do **not** run `hexstrike_mcp.py` by hand. Register it in the client's MCP config; the `--server` URL must point at the already-running Flask server.

`hexstrike-ai-mcp.json` in this repo is a working reference. On this machine it pins an absolute interpreter and the local server:

```json
{
  "mcpServers": {
    "hexstrike-ai": {
      "command": "/home/Odin/hexstrike-ai/hexstrike-dev/bin/python3",
      "args": ["/home/Odin/hexstrike-ai/hexstrike_mcp.py", "--server", "http://127.0.0.1:8888"],
      "timeout": 300,
      "alwaysAllow": []
    }
  }
}
```

Per-client placement:
- **Claude Desktop / Cursor** → `~/.config/Claude/claude_desktop_config.json`, same `mcpServers` shape (use `"disabled": false`).
- **VS Code Copilot** → `.vscode/settings.json` under a `"servers"` key with `"type": "stdio"` (not `mcpServers`).

Notes that matter:
- Prefer an **absolute `command`** path to the venv's `python3` (the one with `fastmcp` installed) rather than a bare `python3`, or the client may launch the wrong interpreter.
- `timeout: 300` — long-running scans need a generous MCP timeout.
- `alwaysAllow: []` keeps tool calls gated (per-call approval); populating it enables autonomous execution — leave empty unless that's intended.
- The `--server` port must match how the Flask server was started (`--port` / `HEXSTRIKE_PORT`).

## How tool availability works

`/health` reports each tool as available/unavailable by running `which <tool>` at request time (see `health_check()` around line 9024, calling `execute_command(f"which {tool}")`). Implications:

- Detection is **live and PATH-based** — installing a tool makes it show up on the next `/health` call with **no server restart**. The server sees whatever PATH it was launched with (`/usr/bin`, `/usr/local/bin`, `~/.local/bin`, `~/go/bin`, `~/.cargo/bin` here).
- Detection matches an **exact command name**. A tool installed under a different binary name (e.g. `shodan` vs the expected `shodan-cli`, `scout` vs `scout-suite`, `bulk_extractor` vs `bulk-extractor`) reads as unavailable even though it's installed — fix with a symlink into `/usr/local/bin` using the name `/health` probes for.

## Request → execution flow

MCP tool call → HTTP `POST /api/tools/<tool>` (or `/api/intelligence/*`, `/api/bugbounty/*`) →
endpoint reads params (`params.get(...)`), assembles a command string →
`execute_command_with_recovery(tool_name, command, ...)` (or plain `execute_command`). That path adds:
result caching (`AdvancedCache`/`HexStrikeCache`), telemetry (`TelemetryCollector`), and
retry/parameter-adjustment/graceful-degradation on failure (`IntelligentErrorHandler`,
`GracefulDegradation`). Most tool endpoints accept `use_recovery` to toggle the recovery wrapper.

## Endpoint families in `hexstrike_server.py`

- `/api/tools/<tool>` — one endpoint per wrapped security tool (the bulk).
- `/api/intelligence/*` — `IntelligentDecisionEngine`: target analysis, tool selection, parameter optimization, attack-chain creation, smart-scan.
- `/api/bugbounty/*` and CTF flows — orchestrated multi-tool playbooks driven by `BugBountyWorkflowManager` / `CTFWorkflowManager` / `CTFToolManager`.
- `/api/processes/*` — async command execution and live process control (list/status/terminate/pause/resume/dashboard) via `EnhancedProcessManager` / `ProcessPool`.
- `/api/files/*`, `/api/payloads/generate`, `/api/cache/*`, `/api/telemetry`, `/api/visual/*` — file ops, exploit/payload generation (`AIExploitGenerator` + per-class `SQLiExploit`/`XSSExploit`/`RCEExploit`/…), cache, telemetry, and terminal-styled visual output (`ModernVisualEngine`).

## Adding or changing a tool

A tool exists in **both files** and both must be edited:
1. Server: add a `@app.route("/api/tools/<name>")` handler in `hexstrike_server.py` that builds the command and calls `execute_command(_with_recovery)`.
2. MCP: add a matching `@mcp.tool()` in `hexstrike_mcp.py` that forwards args via `hexstrike_client.safe_post("api/tools/<name>", {...})`.
3. If the tool should appear in `/health`, ensure its binary name is in the health check's tool list and resolvable on PATH.

## Gotchas specific to this checkout

- There is a **nested duplicate** `hexstrike-ai/hexstrike-ai/` containing another copy of the same files — edit the top-level files unless you deliberately mean the nested clone.
- `hexstrike.log` here is large (tens of MB); it's runtime output, not source.
- Kali's apt mirror on this host is flaky (IPv6 failures / redirector bouncing to dead mirrors). When installing tools via apt use `-o Acquire::ForceIPv4=true -o Acquire::Retries=5 --fix-missing`; apt aborts the whole batch if any one package name has no candidate.
