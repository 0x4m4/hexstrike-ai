#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/bin/hexstrike-agent"
mkdir -p "$ROOT/bin"
cd "$(dirname "$0")"

PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')/$(uname -m)"
echo "[*] Building HexStrike Agent..."
echo "    Platform: $PLATFORM"

go build -ldflags "-s -w" -o "$OUT" .

echo "[✓] Build complete: $OUT"
