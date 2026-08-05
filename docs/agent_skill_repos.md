# Agent Skill and MCP Repositories for HexStrike

This list captures active GitHub repositories that can help agents work with HexStrike and MCP tooling. Use this file as a curated starting point, then re-run `gh search repos` periodically.

## Recommended repositories

### 1) Cursor skill collections

- `spencerpauly/awesome-cursor-skills`
  - URL: <https://github.com/spencerpauly/awesome-cursor-skills>
  - Why it helps: Curated index for reusable Cursor skills and patterns; useful to bootstrap a dedicated HexStrike skill pack.
  - Snapshot: 173 stars, updated 2026-04-23.

- `Pa55w0rd/secknowledge-skill`
  - URL: <https://github.com/Pa55w0rd/secknowledge-skill>
  - Why it helps: Security-focused skill content for Cursor/Claude workflows; useful as a source for pentest safety prompts and checklists.
  - Snapshot: 33 stars, updated 2026-04-22.

### 2) MCP security/tooling indexes

- `Ta0ing/MCP-SecurityTools`
  - URL: <https://github.com/Ta0ing/MCP-SecurityTools>
  - Why it helps: Large security-oriented MCP list to discover complementary servers and operational patterns.
  - Snapshot: 398 stars, updated 2026-04-20.

- `mcp-security-standard/mcp-server-security-standard`
  - URL: <https://github.com/mcp-security-standard/mcp-server-security-standard>
  - Why it helps: Provides a security baseline/checklist for MCP server hardening and trust controls.
  - Snapshot: 72 stars, updated 2026-04-15.

### 3) MCP integration/automation projects

- `patruff/ollama-mcp-bridge`
  - URL: <https://github.com/patruff/ollama-mcp-bridge>
  - Why it helps: Shows MCP bridge patterns that can inform future HexStrike GUI backend architecture.
  - Snapshot: 970 stars, updated 2026-04-20.

- `rectalogic/langchain-mcp`
  - URL: <https://github.com/rectalogic/langchain-mcp>
  - Why it helps: Demonstrates tool invocation orchestration patterns that can be repurposed for HexStrike workflow planners.
  - Snapshot: 205 stars, updated 2026-03-31.

## HexStrike update status check

Use these commands to check update drift between this fork and upstream:

- `gh api repos/0x4m4/hexstrike-ai/commits/master --jq '{sha:.sha,date:.commit.author.date,message:.commit.message}'`
- `gh api repos/<your-org-or-user>/hexstrike-ai/commits/master --jq '{sha:.sha,date:.commit.author.date,message:.commit.message}'`
- `gh api repos/<your-org-or-user>/hexstrike-ai/compare/master...0x4m4:master --jq '{status:.status,ahead_by:.ahead_by,behind_by:.behind_by,total_commits:.total_commits}'`

Current snapshot in this environment:

- Upstream latest commit: `83337796dcfb8cfbf733bd24d0b2c7e4f0732790` (2026-03-06, "Add MIT License")
- Fork latest commit: `07d88053c1175416830117431189935839cedc90` (2025-09-09)
- Compare result: fork is `ahead_by: 4`, `behind_by: 0`.

## How to convert these repos into local skills

1. Pick 1-2 repos from above and extract only patterns relevant to HexStrike operations.
2. Create task-oriented skill docs under `skills/` (for example: `skills/hexstrike_recon.md`, `skills/hexstrike_cloud.md`).
3. Add explicit entry/exit criteria for each skill:
   - Entry: when to use the skill.
   - Steps: ordered command/tool sequence.
   - Exit: what evidence must be captured before reporting success.
4. Link each skill from `AGENTS.md`.
