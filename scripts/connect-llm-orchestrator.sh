#!/usr/bin/env bash
# Connect a running local LLM (llama-server :8080 preferred, else Ollama :11434)
# to HexStrike .env and run a defense-prompted handshake.
#
# Usage:
#   bash scripts/connect-llm-orchestrator.sh
#   bash scripts/connect-llm-orchestrator.sh --status
#   bash scripts/connect-llm-orchestrator.sh --handshake
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

MODE="connect"
PROBE="both"
for arg in "$@"; do
  case "$arg" in
    --status) MODE="status" ;;
    --handshake) MODE="handshake" ;;
    --probe=*) PROBE="${arg#--probe=}" ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
  esac
done

python3 - <<PY
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "${ROOT}/src")
from hexstrike.llm.provider import (
    LocalLlmProvider,
    resolve_llm_config,
    write_env_llm_block,
)

root = Path("${ROOT}")
env_path = root / ".env"
mode = "${MODE}"
probe = "${PROBE}"

cfg = resolve_llm_config()
print(f"[connect-llm] detected provider={cfg.provider} base={cfg.base_url}")
print(f"[connect-llm] llama_reachable={cfg.llama_reachable} ollama_reachable={cfg.ollama_reachable}")
print(f"[connect-llm] priority={','.join(cfg.priority)}")

if mode == "status":
    st = LocalLlmProvider(cfg).status()
    print(json.dumps(st, indent=2))
    sys.exit(0 if st.get("selected_provider_reachable") else 1)

# connect: persist into .env (auto-detect keys; do not pin dead endpoint)
if not env_path.is_file() and (root / ".env.example").is_file():
    env_path.write_text((root / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[connect-llm] seeded {env_path} from .env.example")

write_env_llm_block(env_path, cfg)
print(f"[connect-llm] wrote LLM_* discovery block -> {env_path}")

# Re-resolve after .env write; keep process env hosts distinct
os.environ["LLM_MODEL"] = cfg.model
os.environ["LLAMA_SERVER_HOST"] = cfg.llama_host
os.environ["OLLAMA_HOST"] = cfg.ollama_host
# Clear pins so resolve_llm_config can fall back by priority
os.environ.pop("LLM_PROVIDER", None)
os.environ.pop("LLM_BASE_URL", None)

provider = LocalLlmProvider(resolve_llm_config())
if mode in ("connect", "handshake"):
    report = provider.handshake(probe=probe)
    print(json.dumps(report, indent=2))
    ok = bool(report.get("llm", {}).get("selected_provider_reachable"))
    defense = report.get("defense_chat") or {}
    if defense and not defense.get("ok"):
        print("[connect-llm] WARN: defense chat probe failed — server may still be starting", file=sys.stderr)
    sys.exit(0 if ok else 1)
PY
