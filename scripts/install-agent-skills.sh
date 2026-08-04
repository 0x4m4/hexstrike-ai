#!/usr/bin/env bash
# Install agent skills into Cursor project context.
# Upstream collections:
#   - addyosmani/agent-skills (engineering workflows)
#   - anthropics/skills (official: mcp-builder, skill-creator, docs)
#   - muratcankoylan/Agent-Skills-for-Context-Engineering
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx not found; clone upstream manually and sync into .cursor/skills/"
  exit 1
fi

install_repo() {
  local repo="$1"
  echo "==> Installing ${repo}"
  npx --yes skills add "${repo}" --agent cursor --skill '*' -y
}

install_repo addyosmani/agent-skills
install_repo anthropics/skills
install_repo muratcankoylan/Agent-Skills-for-Context-Engineering

mkdir -p .cursor/skills
if command -v rsync >/dev/null 2>&1; then
  rsync -a .agents/skills/ .cursor/skills/
else
  cp -a .agents/skills/. .cursor/skills/
fi

RULE_FILE=".cursor/rules/agent-skills.mdc"
if [[ ! -f "$RULE_FILE" ]]; then
  echo "Warning: $RULE_FILE missing — create routing rule per docs/cursor-setup.md"
fi

echo "==> Installed $(find .cursor/skills -name SKILL.md | wc -l | tr -d ' ') skills under .cursor/skills/"
echo "Note: VoltAgent/awesome-agent-skills is a curated list (README only), not installable via npx."
echo "Browse: https://github.com/VoltAgent/awesome-agent-skills"
