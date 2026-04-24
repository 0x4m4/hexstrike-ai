# HexStrike Interface Usage (CLI now, GUI-ready next)

This guide defines one interface surface that works immediately for CLI-driven MCP clients and can be reused later by a GUI shell.

Machine-readable surface definition:

- `hexstrike-tool-surface.json`

## 1) Run the backend server

From repository root:

1. `python3 -m venv hexstrike-env`
2. `source hexstrike-env/bin/activate`
3. `python3 -m pip install -r requirements.txt`
4. `python3 hexstrike_server.py --port 8888`

Verify:

- `curl http://127.0.0.1:8888/health`

## 2) Configure MCP client profiles (CLI and agent clients)

Use `hexstrike-ai-mcp.json` as the canonical profile template:

- `hexstrike-ai-guided`: safe default profile with planning/discovery tools in `alwaysAllow`.
- `hexstrike-ai-full-auto`: disabled-by-default profile for full autonomy.

Replace `/absolute/path/to/hexstrike-ai/hexstrike_mcp.py` with your local path.

## 3) CLI-first workflow (recommended baseline)

Start with guided profile:

1. `server_health`
2. `analyze_target_intelligence`
3. `select_optimal_tools_ai`
4. `optimize_tool_parameters_ai`
5. `intelligent_smart_scan`
6. `list_active_processes` / `get_process_dashboard` to monitor long jobs

This sequence is deterministic and should be preserved as the default GUI "Quick Scan" flow.

## 4) Interface contract for future GUI

Treat the server REST routes as the stable contract; GUI views should map to these route groups:

- Health and environment: `/health`, `/api/telemetry`, `/api/cache/stats`
- Tool execution: `/api/tools/*`
- Process management: `/api/processes/*`
- AI orchestration: `/api/intelligence/*`
- Workflows: `/api/bugbounty/*`

## 5) Suggested GUI information architecture

Use these pages/tabs:

1. **Connect**: server URL, profile selection, health card.
2. **Target Analysis**: target input + `analyze_target_intelligence` results.
3. **Tool Plan**: selected tools + optimized parameters + overrides.
4. **Execution**: run/pause/resume/terminate with process dashboard.
5. **Findings**: vulnerabilities, severity rollup, and export actions.

## 6) GUI bootstrap backlog

Keep this as implementation order:

1. Build read-only dashboard (health + telemetry + process list).
2. Add guided quick-scan wizard (target -> plan -> execute).
3. Add tool-specific forms generated from MCP tool signatures.
4. Add profile editor for `alwaysAllow` presets.
5. Add run history and artifact links.

## 7) Operational notes

- Keep `hexstrike-ai-guided` as default profile for demos and new operators.
- Enable unrestricted profile only after server health and tool inventory checks pass.
- Document any local endpoint or profile changes in this file and `AGENTS.md`.
