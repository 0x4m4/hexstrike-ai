#!/usr/bin/env bash
# Mac: получить ветку forensics и запустить 3 прогона (если pull в master конфликтует)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BRANCH="${HEXSTRIKE_FORENSICS_BRANCH:-cursor/forensics-workflows-fix-58a3}"

echo "=== HexStrike Mac forensics bootstrap ==="
echo "repo: $ROOT"
echo "branch: $BRANCH"

git fetch origin "$BRANCH"

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
  git pull origin "$BRANCH" --rebase || git reset --hard "origin/$BRANCH"
else
  git checkout -B "$BRANCH" "origin/$BRANCH"
fi

if [[ ! -f scripts/forensics-env-mac.sh ]]; then
  echo "[FAIL] scripts/forensics-env-mac.sh не найден — checkout не удался"
  exit 1
fi

# shellcheck source=/dev/null
source scripts/forensics-env-mac.sh
bash scripts/run-three-progons.sh
