"""Ensure src/ and scripts/ are on sys.path for hybrid imports."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BOOTSTRAPPED = False


def bootstrap_paths() -> Path:
    global _BOOTSTRAPPED
    if not _BOOTSTRAPPED:
        src = str(ROOT / "src")
        scripts = str(ROOT / "scripts")
        if src not in sys.path:
            sys.path.insert(0, src)
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        _BOOTSTRAPPED = True
    return ROOT
