"""Shared helpers for reading artifacts/master_context.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MASTER_CONTEXT_PATH = ROOT / "artifacts" / "master_context.json"


def load_master_context(path: Path | None = None) -> dict[str, Any] | None:
    """Load unified context index if present."""
    ctx_path = path or MASTER_CONTEXT_PATH
    if not ctx_path.is_file():
        return None
    try:
        return json.loads(ctx_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def iter_entries(context: dict[str, Any]) -> list[dict[str, Any]]:
    entries = context.get("entries", [])
    return entries if isinstance(entries, list) else []


def get_entry_data(
    entity_type: str | None = None,
    *,
    source_contains: str | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Return payload for the first matching indexed artifact."""
    context = load_master_context(path)
    if not context:
        return None

    for entry in iter_entries(context):
        meta = entry.get("_meta", {})
        if entity_type and meta.get("entity_type") != entity_type:
            continue
        if source_contains and source_contains not in meta.get("source_file", ""):
            continue
        data = entry.get("data")
        return data if isinstance(data, dict) else entry

    return None


def get_cex_cluster_payload(path: Path | None = None) -> dict[str, Any] | None:
    """Resolve CEX cluster map from unified context."""
    data = get_entry_data("cex_cluster_map", path=path)
    if data:
        return data
    return get_entry_data(source_contains="cex-cluster-map", path=path)
