#!/usr/bin/env python3
"""Lightweight persistent RAG layer for forensic artifact history (LanceDB + HDD)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# Primary storage: secondary disk on Mac operator workstation.
DEFAULT_RAG_ROOT = Path("/Volumes/Eva/rag-storage")
RAG_ROOT = Path(os.environ.get("RAG_STORAGE_ROOT", str(DEFAULT_RAG_ROOT)))
VECTOR_DIR = RAG_ROOT / "vectors"
TABLE_NAME = "forensics_history"
FEEDBACK_TABLE = "forensics_feedback"
EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "120"))

_model = None


class RagStorageError(RuntimeError):
    """Raised when RAG storage is unavailable."""


def check_storage_mount() -> Path:
    """Verify Eva disk is mounted and storage path is usable."""
    if not DEFAULT_RAG_ROOT.parent.exists():
        raise RagStorageError(
            f"Disk not mounted: {DEFAULT_RAG_ROOT.parent} does not exist. "
            "Mount /Volumes/Eva/ or set RAG_STORAGE_ROOT to a writable path."
        )
    if not os.access(DEFAULT_RAG_ROOT.parent, os.W_OK):
        raise RagStorageError(
            f"Disk not writable: {DEFAULT_RAG_ROOT.parent}. "
            "Check mount permissions or set RAG_STORAGE_ROOT."
        )
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    return VECTOR_DIR


def resolve_vector_dir() -> Path:
    """Resolve vector DB directory, with optional cloud/lab override."""
    if os.environ.get("RAG_STORAGE_ROOT"):
        path = Path(os.environ["RAG_STORAGE_ROOT"]) / "vectors"
        path.mkdir(parents=True, exist_ok=True)
        return path

    if sys.platform == "darwin":
        return check_storage_mount()

    # Non-macOS lab fallback for CI/cloud testing
    fallback = ROOT / "rag-storage" / "vectors"
    fallback.mkdir(parents=True, exist_ok=True)
    print(f"[!] /Volumes/Eva not available on {sys.platform}; using fallback: {fallback}")
    return fallback


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [vec.tolist() for vec in vectors]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def file_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect_db(vector_dir: Path | None = None):
    import lancedb

    db_path = vector_dir or resolve_vector_dir()
    return lancedb.connect(str(db_path))


def _table_names(db) -> list[str]:
    list_tables = getattr(db, "list_tables", None)
    if callable(list_tables):
        result = list_tables()
        if hasattr(result, "tables"):
            return list(result.tables)
        return list(result)
    return list(db.table_names())


def ensure_table(db, bootstrap_rows: list[dict[str, Any]] | None = None):
    if TABLE_NAME in _table_names(db):
        return db.open_table(TABLE_NAME)
    if not bootstrap_rows:
        raise RagStorageError(
            f"Table '{TABLE_NAME}' does not exist yet. Index at least one document first."
        )
    return db.create_table(TABLE_NAME, data=bootstrap_rows)


def index_document(
    file_path: str | Path,
    content: str | None = None,
    *,
    label: str = "",
    table_name: str = TABLE_NAME,
) -> dict[str, Any]:
    """Chunk content, embed, and store in LanceDB with metadata."""
    path = Path(file_path)
    if content is None:
        if not path.is_file():
            raise FileNotFoundError(path)
        content = path.read_text(encoding="utf-8", errors="replace")

    chunks = chunk_text(content)
    if not chunks:
        return {"indexed": 0, "source_file": str(path)}

    db = connect_db()
    source = str(path.resolve() if path.exists() else path)
    ts = file_timestamp(path) if path.exists() else datetime.now(tz=timezone.utc).isoformat()
    vectors = embed_texts(chunks)

    rows = []
    for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
        row = {
            "id": str(uuid.uuid4()),
            "vector": vector,
            "text": chunk,
            "source_file": source,
            "timestamp": ts,
            "chunk_index": idx,
        }
        if table_name == FEEDBACK_TABLE:
            row["label"] = label or "false_positive"
        rows.append(row)

    if table_name in _table_names(db):
        table = db.open_table(table_name)
        table.add(rows)
    else:
        db.create_table(table_name, data=rows)
        table = db.open_table(table_name)

    return {"indexed": len(rows), "source_file": source, "timestamp": ts}


def search_history(
    query_text: str,
    top_k: int = 3,
    *,
    label: str | None = None,
    table_name: str = TABLE_NAME,
) -> list[dict[str, Any]]:
    """Vector similarity search over forensic history."""
    db = connect_db()
    if table_name not in _table_names(db):
        return []

    table = db.open_table(table_name)
    if table.count_rows() == 0:
        return []

    query_vector = embed_texts([query_text])[0]
    fetch_k = top_k * 4 if label else top_k
    results = (
        table.search(query_vector)
        .metric("cosine")
        .limit(fetch_k)
        .to_list()
    )

    hits: list[dict[str, Any]] = []
    for row in results:
        row_label = row.get("label") or ""
        if label and row_label != label:
            continue
        hits.append({
            "source_file": row.get("source_file", ""),
            "timestamp": row.get("timestamp", ""),
            "chunk_index": row.get("chunk_index", 0),
            "snippet": row.get("text", "")[:500],
            "score": row.get("_distance"),
            "label": row_label,
        })
        if len(hits) >= top_k:
            break
    return hits


def index_false_positive(
    tx_hash: str,
    from_addr: str,
    to_addr: str,
    note: str = "",
) -> dict[str, Any]:
    """Store operator feedback as a labeled false-positive pattern in RAG."""
    payload = {
        "label": "false_positive",
        "tx_hash": tx_hash.lower(),
        "from": from_addr.lower(),
        "to": to_addr.lower(),
        "note": note,
        "indexed_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    text = json.dumps(payload, ensure_ascii=False)
    virtual_path = f"feedback/false_positive/{tx_hash.lower()}.json"
    return index_document(virtual_path, text, label="false_positive", table_name=FEEDBACK_TABLE)


def is_false_positive_pattern(tx_hash: str, from_addr: str, to_addr: str) -> tuple[bool, list[dict[str, Any]]]:
    """Check RAG for similar false-positive patterns before alerting."""
    frm = from_addr.lower()
    to = to_addr.lower()
    tx_hash_l = tx_hash.lower()
    query = (
        f"false_positive label transaction pattern "
        f"from {frm} to {to} hash {tx_hash_l}"
    )
    try:
        hits = search_history(query, top_k=3, label="false_positive", table_name=FEEDBACK_TABLE)
    except (RagStorageError, OSError, ImportError):
        return False, []

    for hit in hits:
        snippet = hit.get("snippet", "").lower()
        score = hit.get("score") or 1.0
        if tx_hash_l in snippet:
            return True, hits
        if frm in snippet and to in snippet and score < 0.75:
            return True, hits
    return False, hits


def index_path(target: Path) -> dict[str, Any]:
    """Index a single file or all JSON/text files under a directory."""
    if target.is_file():
        content = target.read_text(encoding="utf-8", errors="replace")
        return index_document(target, content)

    if not target.is_dir():
        raise FileNotFoundError(target)

    summary = {"files": 0, "chunks": 0, "errors": []}
    patterns = ("*.json", "*.md", "*.txt", "*.jsonl")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(target.rglob(pattern)))

    for file_path in files:
        if file_path.name == "master_context.json":
            continue
        try:
            result = index_document(file_path)
            summary["files"] += 1
            summary["chunks"] += result.get("indexed", 0)
        except Exception as exc:
            summary["errors"].append({"file": str(file_path), "error": str(exc)})

    return summary


def cmd_status() -> int:
    try:
        vector_dir = resolve_vector_dir()
    except RagStorageError as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"RAG root:      {RAG_ROOT}")
    print(f"Vector dir:    {vector_dir}")
    print(f"Eva mounted:   {DEFAULT_RAG_ROOT.parent.exists()}")
    print(f"Model:         {EMBEDDING_MODEL}")

    if TABLE_NAME in _table_names(connect_db(vector_dir)):
        table = connect_db(vector_dir).open_table(TABLE_NAME)
        print(f"Table rows:    {table.count_rows()}")
    else:
        print("Table rows:    0 (table not created yet)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Forensic RAG core (LanceDB + sentence-transformers)")
    parser.add_argument("--index-all", metavar="PATH", help="Index all artifacts under PATH")
    parser.add_argument("--index-file", metavar="FILE", help="Index a single file")
    parser.add_argument("--search", metavar="QUERY", help="Semantic search query")
    parser.add_argument("--top-k", type=int, default=3, help="Search result count")
    parser.add_argument("--status", action="store_true", help="Show storage status")
    args = parser.parse_args()

    if args.status:
        return cmd_status()

    if args.index_file:
        try:
            result = index_document(args.index_file)
            print(json.dumps({"success": True, **result}, indent=2))
            return 0
        except (RagStorageError, FileNotFoundError, OSError) as exc:
            print(json.dumps({"success": False, "error": str(exc)}))
            return 1

    if args.index_all:
        try:
            summary = index_path(Path(args.index_all))
            print(json.dumps({"success": True, **summary}, indent=2))
            return 0 if not summary.get("errors") else 2
        except (RagStorageError, FileNotFoundError, OSError) as exc:
            print(json.dumps({"success": False, "error": str(exc)}))
            return 1

    if args.search:
        try:
            hits = search_history(args.search, top_k=args.top_k)
            print(json.dumps({"success": True, "query": args.search, "results": hits}, indent=2, ensure_ascii=False))
            return 0
        except RagStorageError as exc:
            print(json.dumps({"success": False, "error": str(exc)}))
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
