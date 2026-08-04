"""Central path resolution for HexStrike-AI."""

from __future__ import annotations

import os
from pathlib import Path

# Project root: two levels up from this file (src/hexstrike/paths.py)
ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_DIR = ROOT / "config"
ARTIFACTS_DIR = ROOT / "artifacts"
SCRIPTS_DIR = ROOT / "scripts"
SRC_DIR = ROOT / "src"

RPC_CONFIG = CONFIG_DIR / "rpc_config.json"
MASTER_CONTEXT = ARTIFACTS_DIR / "master_context.json"
ALERTS_LOG = ARTIFACTS_DIR / "alerts.log"
PENDING_ACTION = ARTIFACTS_DIR / "pending_action.json"
MANIFEST_PATH = ROOT / "project_manifest.json"
INSTRUCTIONS_DIR = ROOT / "src" / "hexstrike" / "instructions"
EVA_MOUNT = Path(os.environ.get("HEXSTRIKE_EVA_MOUNT", "/Volumes/Eva"))
RAG_ROOT = Path(os.environ.get("RAG_STORAGE_ROOT", str(EVA_MOUNT / "rag-storage")))
