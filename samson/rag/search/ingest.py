"""Document ingestion: chunking, hashing, Ollama embeddings, Postgres upsert."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import Database, sha256_text, vector_literal
from samson.core.errors import DatabaseError, EmbeddingError
from samson.core.http_client import OllamaClient
from samson.core.scope import ScopeEnforcer

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\S+")


def _approx_token_count(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(len(tokens), start + chunk_size)
        chunk = " ".join(tokens[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(tokens):
            break
        start = max(0, end - overlap)
    return chunks


class DocumentIngester:
    """Indexes markdown/json/text documents into Postgres + pgvector."""

    def __init__(
        self,
        settings: SamsonSettings | None = None,
        db: Database | None = None,
        ollama: OllamaClient | None = None,
        scope: ScopeEnforcer | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._db = db or Database(self._settings)
        self._ollama = ollama or OllamaClient(self._settings)
        self._scope = scope or ScopeEnforcer(self._settings)
        self._owns_ollama = ollama is None

    def close(self) -> None:
        if self._owns_ollama:
            self._ollama.close()

    def ingest_path(
        self,
        path: Path,
        *,
        doc_type: str,
        project: str,
        environment: str,
        tags: list[str] | None = None,
        confidence: float = 1.0,
    ) -> UUID:
        self._scope.assert_doc_type(doc_type)
        if not path.is_file():
            raise DatabaseError(f"Document not found: {path}", path=str(path))

        raw = path.read_text(encoding="utf-8", errors="replace")
        content_hash = sha256_text(raw)
        existing = self._db.fetchone(
            """
            SELECT doc_id FROM documents
            WHERE source_path = :source_path AND project = :project
              AND environment = :environment AND content_hash = :content_hash
            """,
            {
                "source_path": str(path),
                "project": project,
                "environment": environment,
                "content_hash": content_hash,
            },
        )
        if existing:
            return UUID(str(existing["doc_id"]))

        doc_id = uuid4()
        self._db.execute(
            """
            INSERT INTO documents (
                doc_id, source_path, doc_type, project, environment, tags,
                confidence, content_hash, index_version
            ) VALUES (
                :doc_id, :source_path, :doc_type, :project, :environment, :tags,
                :confidence, :content_hash, :index_version
            )
            """,
            {
                "doc_id": str(doc_id),
                "source_path": str(path),
                "doc_type": doc_type,
                "project": project,
                "environment": environment,
                "tags": tags or [],
                "confidence": confidence,
                "content_hash": content_hash,
                "index_version": self._settings.rag_index_version,
            },
        )

        chunks = _chunk_text(raw, self._settings.rag_chunk_size_tokens, self._settings.rag_chunk_overlap_tokens)
        for index, chunk in enumerate(chunks):
            self._upsert_chunk(doc_id, index, chunk)
        logger.info("Ingested %s (%s chunks)", path, len(chunks))
        return doc_id

    def ingest_directory(
        self,
        root: Path | None = None,
        *,
        doc_type: str = "markdown",
        project: str | None = None,
        environment: str | None = None,
    ) -> list[UUID]:
        root = root or self._settings.rag_docs_path
        project = project or self._settings.project
        environment = environment or self._settings.environment
        doc_ids: list[UUID] = []
        for pattern in ("**/*.md", "**/*.json", "**/*.txt"):
            for path in sorted(root.glob(pattern)):
                doc_ids.append(
                    self.ingest_path(
                        path,
                        doc_type=doc_type if path.suffix != ".json" else "json",
                        project=project,
                        environment=environment,
                    )
                )
        return doc_ids

    def _upsert_chunk(self, doc_id: UUID, chunk_index: int, chunk: str) -> None:
        chunk_id = uuid4()
        content_hash = sha256_text(chunk)
        token_count = _approx_token_count(chunk)
        self._db.execute(
            """
            INSERT INTO document_chunks (chunk_id, doc_id, chunk_index, chunk_text, content_hash, token_count)
            VALUES (:chunk_id, :doc_id, :chunk_index, :chunk_text, :content_hash, :token_count)
            ON CONFLICT (doc_id, chunk_index) DO UPDATE SET
                chunk_text = EXCLUDED.chunk_text,
                content_hash = EXCLUDED.content_hash,
                token_count = EXCLUDED.token_count
            RETURNING chunk_id
            """,
            {
                "chunk_id": str(chunk_id),
                "doc_id": str(doc_id),
                "chunk_index": chunk_index,
                "chunk_text": chunk,
                "content_hash": content_hash,
                "token_count": token_count,
            },
        )
        row = self._db.fetchone(
            "SELECT chunk_id FROM document_chunks WHERE doc_id = :doc_id AND chunk_index = :chunk_index",
            {"doc_id": str(doc_id), "chunk_index": chunk_index},
        )
        if not row:
            raise DatabaseError("Failed to upsert document chunk", doc_id=str(doc_id), chunk_index=chunk_index)
        resolved_chunk_id = UUID(str(row["chunk_id"]))
        embedding = self._embed(chunk)
        dim = len(embedding)
        self._db.execute(
            """
            INSERT INTO embeddings (embedding_id, chunk_id, embedding, embedding_model, embedding_dim)
            VALUES (:embedding_id, :chunk_id, CAST(:embedding AS vector), :embedding_model, :embedding_dim)
            ON CONFLICT (chunk_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model,
                embedding_dim = EXCLUDED.embedding_dim
            """,
            {
                "embedding_id": str(uuid4()),
                "chunk_id": str(resolved_chunk_id),
                "embedding": vector_literal(embedding),
                "embedding_model": self._settings.ollama_embed_model,
                "embedding_dim": dim,
            },
        )

    def _embed(self, text: str) -> list[float]:
        try:
            return self._ollama.embed(text)
        except Exception as exc:
            raise EmbeddingError("Ollama embedding failed during ingest", error=str(exc)) from exc
