#!/usr/bin/env bash
# switch-to-7b.sh — средняя модель deepseek-r1:7b (run on Mac)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HEXSTRIKE_BASE_MODEL=deepseek-r1:7b
export LLM_MODEL=deepseek-r1:7b
export OLLAMA_NUM_PREDICT=128
exec "$ROOT/hexstrike-go.sh"
