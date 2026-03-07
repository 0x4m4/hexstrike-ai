# Using HexStrike with ChatGPT Codex

HexStrike works with Codex through MCP (Model Context Protocol). Here's how to set it up.

## Prerequisites

- HexStrike server running on localhost:8888
- ChatGPT Codex CLI installed

## Configuration

Add to your `~/.codex/config.toml`:

```toml
[mcp_servers.hexstrike-ai]
transport = "stdio"
command = "/absolute/path/to/hexstrike-env/bin/python3"
args = [
    "/absolute/path/to/hexstrike_mcp.py",
    "--server",
    "http://localhost:8888"
]

# Optional: Increase if you get timeout errors
startup_timeout_ms = 20000
```

Replace paths with your actual paths.

## Start the Server

In one terminal:
```bash
python3 hexstrike_server.py --port 8888
```

In another terminal:
```bash
codex
```

Codex will automatically connect to HexStrike's 64 security tools.

## Troubleshooting

**"request timed out"**
- Increase startup_timeout_ms to 30000 or 40000
- Make sure hexstrike_server.py is running first

**"Failed to connect"**
- Check server is on port 8888: `curl http://localhost:8888/health`
- Verify paths in config.toml are absolute, not relative

**Tools not showing up**
- Restart Codex after config changes
- Check logs: `codex --debug`
