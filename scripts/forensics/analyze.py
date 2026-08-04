#!/usr/bin/env python3
"""Forensics analyzer dispatcher — routes to full per-module analyzers."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORENSICS = ROOT / "scripts" / "forensics"

ANALYZERS = {
    "trx": "trx_drainer_analyzer.py",
    "evm": "evm_drainer_analyzer.py",
    "apeterminal": "apeterminal_drainer_analyzer.py",
    "solana": "solana_drainer_analyzer.py",
    "vanilla": "vanilla_drainer_analyzer.py",
    "permit": "permit_farming_analyzer.py",
    "create2": "create2_drainer_analyzer.py",
}


def run_analyzer(kind: str) -> int:
    script = FORENSICS / ANALYZERS[kind]
    spec = importlib.util.spec_from_file_location(f"{kind}_analyzer", script)
    if spec is None or spec.loader is None:
        print(f"Analyzer missing: {script}", file=sys.stderr)
        return 1
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main()


def main() -> int:
    parser = argparse.ArgumentParser(description="HexStrike forensics analyzer")
    parser.add_argument("kind", choices=list(ANALYZERS.keys()))
    args = parser.parse_args()
    return run_analyzer(args.kind)


if __name__ == "__main__":
    raise SystemExit(main())
