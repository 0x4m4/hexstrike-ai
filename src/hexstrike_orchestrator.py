#!/usr/bin/env python3
"""HexStrike orchestrator launcher with OFFLINE_PRIMARY RAG contour."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from hexstrike_rag import LocalRagStore
LOG_PATH = ROOT / "hexstrike.log"
RAG_INDEX_DIR = ROOT / "data" / "rag"


def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def start_api_server(python_bin: Path, port: int) -> subprocess.Popen:
    server_script = ROOT / "hexstrike_server.py"
    if not server_script.exists():
        raise FileNotFoundError(f"Server script not found: {server_script}")

    env = os.environ.copy()
    env["HEXSTRIKE_MODE"] = "OFFLINE_PRIMARY"
    env["HEXSTRIKE_RAG_INDEX"] = str(RAG_INDEX_DIR)

    cmd = [str(python_bin), str(server_script), "--port", str(port)]
    logging.info("Starting HexStrike API server: %s", " ".join(cmd))
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description="HexStrike orchestrator")
    parser.add_argument("--mode", default="OFFLINE_PRIMARY", choices=["OFFLINE_PRIMARY", "ONLINE"])
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--python", default=str(ROOT / "hexstrike-env" / "bin" / "python3"))
    parser.add_argument("--skip-server", action="store_true")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("hexstrike.orchestrator")
    logger.info("HexStrike orchestrator boot | mode=%s", args.mode)

    rag = LocalRagStore(root=ROOT, index_dir=RAG_INDEX_DIR)
    rag_meta = rag.build_index()
    logger.info("RAG contour initialized: %s", rag_meta)

    sample = rag.query("telemetry technology-detect nuclei-scan")
    logger.info("RAG smoke query returned %d chunks", len(sample))

    if args.skip_server:
        logger.info("Server launch skipped (--skip-server)")
        return 0

    python_bin = Path(args.python)
    if not python_bin.exists():
        logger.error("Python interpreter not found: %s", python_bin)
        return 1

    process = start_api_server(python_bin=python_bin, port=args.port)
    logger.info("HexStrike API PID=%s", process.pid)

    try:
        while process.poll() is None:
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Shutdown requested, terminating API server")
        process.terminate()
        process.wait(timeout=10)

    return process.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
