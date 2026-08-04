"""Small helpers for sandbox JSONL artifact files."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = int(os.environ.get("SANDBOX_LOG_MAX_BYTES", str(5 * 1024 * 1024)))


def rotate_if_needed(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    if not path.is_file() or path.stat().st_size <= max_bytes:
        return
    rotated = path.with_name(f"{path.name}.1")
    if rotated.exists():
        rotated.unlink()
    path.rename(rotated)


def append_jsonl(path: Path, entry: dict[str, Any], *, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rotate_if_needed(path, max_bytes)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
