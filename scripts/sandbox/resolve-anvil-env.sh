#!/usr/bin/env bash
# resolve-anvil-env.sh — print path to sandbox env file (creates anvil.env if needed)
set -euo pipefail
SANDBOX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${SANDBOX_ENV:-}" ]]; then
  echo "$SANDBOX_ENV"
elif [[ -f "$SANDBOX/anvil.env" ]]; then
  echo "$SANDBOX/anvil.env"
else
  "$SANDBOX/setup-anvil-env.sh"
  echo "$SANDBOX/anvil.env"
fi
