# AGENTS.md

## Purpose
This repository ships the HexStrike MCP client and API server, plus local configuration and documentation for running it safely from AI agents.

## Agent Priorities
1. Keep HexStrike integration usable in both CLI-first and future GUI-first workflows.
2. Keep MCP tool usage explicit, scope-limited, and authorization-aware.
3. Keep setup instructions reproducible for Cursor, Claude Desktop, and similar MCP clients.

## Standard Workflow For Changes
1. **Check upstream status first** with GitHub CLI:
   - `gh api repos/0x4m4/hexstrike-ai/commits/master --jq '{sha:.sha,date:.commit.author.date,message:.commit.message}'`
   - `gh api repos/jlevydesigndev-glitch/hexstrike-ai/compare/master...0x4m4:master --jq '{status:.status,ahead_by:.ahead_by,behind_by:.behind_by,total_commits:.total_commits}'`
2. **Review interface docs** before config changes:
   - `docs/interface_usage.md`
   - `hexstrike-tool-surface.json`
3. **Validate config files** after edits:
   - `python3 -m json.tool hexstrike-ai-mcp.json >/dev/null`
   - `python3 -m json.tool hexstrike-tool-surface.json >/dev/null`
4. **Run server health check** when runtime behavior is touched:
   - `python3 hexstrike_server.py`
   - `curl http://127.0.0.1:8888/health`

## MCP Safety Defaults
- Start from a guided `alwaysAllow` profile and only expand tool allowlists when required.
- Prefer reconnaissance and planning tools before exploitation-oriented tools.
- Do not run destructive, high-noise, or out-of-scope scans without explicit operator direction.
- Keep legal authorization assumptions explicit in prompts and reports.

## Skill and Knowledge Sources
- Use `docs/agent_skill_repos.md` as the current shortlist of external skill repositories and MCP security references.
- When adding a new external skill source, capture:
  - repository URL
  - why it helps HexStrike workflows
  - expected risks (prompt injection, stale procedures, unsafe defaults)

## Cursor Cloud specific instructions
- Keep docs updates lightweight and versioned in-repo so future cloud agents can start without rebuilding context.
- If interface structure changes, update both:
  - `hexstrike-tool-surface.json` (machine-readable surface definition)
  - `docs/interface_usage.md` (human-readable explanation)
