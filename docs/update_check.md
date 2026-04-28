# HexStrike Upstream Update Check

This project is currently a fork of `0x4m4/hexstrike-ai`.

## Current status snapshot

Run the following from repository root:

- `gh repo view 0x4m4/hexstrike-ai --json updatedAt,defaultBranchRef,url`
- `gh api repos/0x4m4/hexstrike-ai/commits/master --jq '{sha:.sha,date:.commit.author.date,message:.commit.message}'`
- `gh api repos/jlevydesigndev-glitch/hexstrike-ai/commits/master --jq '{sha:.sha,date:.commit.author.date,message:.commit.message}'`
- `gh api repos/jlevydesigndev-glitch/hexstrike-ai/compare/master...0x4m4:master --jq '{status:.status,ahead_by:.ahead_by,behind_by:.behind_by,total_commits:.total_commits}'`

At the time this document was created:

- Upstream (`0x4m4/hexstrike-ai`) latest commit was `83337796dcfb8cfbf733bd24d0b2c7e4f0732790` (2026-03-06).
- This fork (`jlevydesigndev-glitch/hexstrike-ai`) latest commit was `07d88053c1175416830117431189935839cedc90` (2025-09-09).
- Compare result reported this fork as `ahead_by: 4, behind_by: 0` against upstream master.

## Routine update workflow

1. Verify local working tree is clean.
2. Fetch latest upstream metadata:
   - `git remote add upstream https://github.com/0x4m4/hexstrike-ai.git` (one-time)
   - `git fetch upstream master`
3. Inspect diff scope:
   - `git log --oneline master..upstream/master`
   - `git log --oneline upstream/master..master`
4. Merge or cherry-pick based on desired sync strategy.
5. Re-run smoke tests:
   - `python3 -m py_compile hexstrike_mcp.py hexstrike_server.py`
   - `python3 hexstrike_server.py --help`
   - `python3 hexstrike_mcp.py --help`
6. Update documentation if endpoints/tools changed.

## Release monitoring

`gh release list -R 0x4m4/hexstrike-ai --limit 10`

If the list is empty, rely on commit activity and README changes.
