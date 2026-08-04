#!/usr/bin/env python3
"""Local RAG contour for HexStrike (OFFLINE_PRIMARY mode)."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger("hexstrike.rag")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
DEFAULT_INDEX_DIRS = ("README.md", "hexstrike_cli.py", "hexstrike_mcp.py", "hexstrike_server.py")


@dataclass
class RagChunk:
    chunk_id: str
    source: str
    text: str
    tokens: List[str]


class LocalRagStore:
    """Lightweight local knowledge index without external vector DB."""

    def __init__(self, root: Path, index_dir: Path):
        self.root = root
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "chunks.json"
        self.meta_path = self.index_dir / "meta.json"
        self.chunks: List[RagChunk] = []

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token.lower() for token in re.findall(r"[a-zA-Z0-9_./:-]{3,}", text)]

    def _chunk_text(self, source: str, text: str) -> List[RagChunk]:
        chunks: List[RagChunk] = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(len(text), start + CHUNK_SIZE)
            piece = text[start:end].strip()
            if piece:
                chunk_id = f"{source}::{idx}"
                chunks.append(RagChunk(chunk_id=chunk_id, source=source, text=piece, tokens=self._tokenize(piece)))
                idx += 1
            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
        return chunks

    def _load_source(self, rel_path: str) -> str:
        path = self.root / rel_path
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def build_index(self, sources: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        started = time.time()
        selected = list(sources or DEFAULT_INDEX_DIRS)
        self.chunks = []

        for source in selected:
            text = self._load_source(source)
            if not text:
                logger.warning("RAG skip missing source: %s", source)
                continue
            self.chunks.extend(self._chunk_text(source, text))
            logger.info("RAG indexed source=%s chunks=%d", source, len(self.chunks))

        payload = [asdict(chunk) for chunk in self.chunks]
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        meta = {
            "mode": "OFFLINE_PRIMARY",
            "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sources": selected,
            "chunk_count": len(self.chunks),
            "duration_seconds": round(time.time() - started, 2),
        }
        self.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("RAG index ready: %d chunks in %.2fs", len(self.chunks), meta["duration_seconds"])
        return meta

    def load_index(self) -> bool:
        if not self.index_path.exists():
            return False
        raw = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.chunks = [RagChunk(**item) for item in raw]
        return True

    def query(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.chunks and not self.load_index():
            return []

        q_tokens = set(self._tokenize(question))
        if not q_tokens:
            return []

        scored: List[tuple[float, RagChunk]] = []
        for chunk in self.chunks:
            overlap = len(q_tokens.intersection(chunk.tokens))
            if overlap == 0:
                continue
            score = overlap / max(len(q_tokens), 1)
            scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, chunk in scored[:top_k]:
            results.append(
                {
                    "score": round(score, 4),
                    "source": chunk.source,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text[:500],
                }
            )
        return results
