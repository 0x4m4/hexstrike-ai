#!/usr/bin/env bash
# run-target-recon.sh — wrapper: multi-wallet recon (replaces append-only legacy flow)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python3 "$ROOT/scripts/sandbox/run-multi-wallet-recon.py" "$@"
