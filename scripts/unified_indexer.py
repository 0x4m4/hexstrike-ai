#!/usr/bin/env python3
"""Recursively index JSON artifacts into artifacts/master_context.json."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACTS_DIR = ROOT / "artifacts"
MASTER_CONTEXT_FILE = DEFAULT_ARTIFACTS_DIR / "master_context.json"
INDEX_VERSION = "1.0"
SKIP_FILES = {"master_context.json"}


def infer_entity_type(rel_path: str, data: Any) -> str:
    """Heuristic entity classification from path and payload."""
    lower = rel_path.lower()
    name = Path(lower).stem

    if "cex-cluster-map" in lower or name == "cex_cluster_map":
        return "cex_cluster_map"
    if "entity-id" in lower or name == "entity_id":
        return "entity_id"
    if "exchange-forensics" in lower:
        return "exchange_forensics"
    if "recon-master" in lower or "recon" in lower:
        return "recon_report"
    if "rpc" in lower and ("phase" in lower or "orchestrator" in lower or "crypto-rpc" in lower):
        return "rpc_probe"
    if "orchestrator" in lower:
        return "orchestrator_run"
    if "multichain-cluster" in lower:
        return "multichain_cluster"
    if "infra-targets" in lower:
        return "infra_targets"
    if "jenkins" in lower or "cve" in lower:
        return "vuln_intel"
    if "lea" in lower:
        return "lea_pack"
    if isinstance(data, dict):
        if data.get("type") == "law_enforcement_request_pack":
            return "lea_pack"
        if data.get("task") == "trace-funds (read-only)":
            return "cex_cluster_map"
        if data.get("agent"):
            agent = str(data["agent"]).lower()
            if "graph" in agent:
                return "cex_cluster_map"
            if "osint" in agent:
                return "entity_id"
    return "artifact"


def file_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_entry(source_file: Path, artifacts_root: Path) -> dict[str, Any] | None:
    try:
        raw = source_file.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[!] skip {source_file}: {exc}")
        return None

    rel = source_file.relative_to(artifacts_root).as_posix()
    entity_type = infer_entity_type(rel, data)
    entry_id = re.sub(r"[^a-zA-Z0-9._-]+", "-", rel.replace("/", "__"))

    return {
        "id": entry_id,
        "_meta": {
            "source_file": f"artifacts/{rel}",
            "timestamp": file_timestamp(source_file),
            "entity_type": entity_type,
        },
        "data": data,
    }


def scan_artifacts(artifacts_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not artifacts_dir.is_dir():
        return entries

    for path in sorted(artifacts_dir.rglob("*.json")):
        if path.name in SKIP_FILES:
            continue
        entry = build_entry(path, artifacts_dir)
        if entry:
            entries.append(entry)
    return entries


def build_index(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_entity: dict[str, list[str]] = {}
    by_source: dict[str, str] = {}

    for entry in entries:
        meta = entry["_meta"]
        entry_id = entry["id"]
        by_source[meta["source_file"]] = entry_id
        by_entity.setdefault(meta["entity_type"], []).append(entry_id)

    return {
        "index_version": INDEX_VERSION,
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_count": len(entries),
        "entries": entries,
        "by_entity_type": by_entity,
        "by_source_file": by_source,
    }


def write_index(index: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build artifacts/master_context.json")
    parser.add_argument("--artifacts-dir", type=Path, default=DEFAULT_ARTIFACTS_DIR)
    parser.add_argument("--output", type=Path, default=MASTER_CONTEXT_FILE)
    args = parser.parse_args()

    entries = scan_artifacts(args.artifacts_dir)
    index = build_index(entries)
    write_index(index, args.output)

    print(f"[+] Indexed {len(entries)} JSON file(s) -> {args.output}")
    for entity_type, ids in sorted(index["by_entity_type"].items()):
        print(f"    {entity_type}: {len(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
