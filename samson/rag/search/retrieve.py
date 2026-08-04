"""Semantic retrieval with pgvector and metadata filters."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import Database, vector_literal
from samson.core.errors import EmbeddingError
from samson.core.http_client import OllamaClient
from samson.core.scope import ScopeEnforcer
from samson.rag.schemas import ChunkResult, RetrieveContextRequest, RetrieveContextResponse

logger = logging.getLogger(__name__)


class ContextRetriever:
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

    def retrieve(self, req: RetrieveContextRequest) -> RetrieveContextResponse:
        self._scope.assert_operator(req.operator_id, request_id=req.request_id)

        try:
            query_embedding = self._ollama.embed(req.query)
        except Exception as exc:
            raise EmbeddingError("Failed to embed retrieval query", error=str(exc)) from exc

        filters: dict[str, Any] = {
            "project": req.project,
            "environment": req.environment,
            "tags": req.tags,
            "scenario_type": req.scenario_type,
        }

        params: dict[str, Any] = {
            "project": req.project,
            "environment": req.environment,
            "embedding": vector_literal(query_embedding),
            "top_k": req.top_k,
            "index_version": self._settings.rag_index_version,
        }

        tag_clause = ""
        if req.tags:
            tag_clause = "AND d.tags && :tags"
            params["tags"] = req.tags

        sql = f"""
            SELECT
                c.chunk_id,
                c.doc_id,
                c.chunk_text,
                c.content_hash,
                d.source_path,
                d.doc_type,
                d.tags,
                1 - (e.embedding <=> CAST(:embedding AS vector)) AS score
            FROM embeddings e
            JOIN document_chunks c ON c.chunk_id = e.chunk_id
            JOIN documents d ON d.doc_id = c.doc_id
            WHERE d.project = :project
              AND d.environment = :environment
              AND d.index_version = :index_version
              {tag_clause}
            ORDER BY e.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """
        rows = self._db.fetchall(sql, params)
        chunks: list[ChunkResult] = []
        for row in rows:
            text = str(row["chunk_text"])
            chunks.append(
                ChunkResult(
                    chunk_id=UUID(str(row["chunk_id"])),
                    doc_id=UUID(str(row["doc_id"])),
                    score=float(row["score"]),
                    source_path=str(row["source_path"]),
                    doc_type=str(row["doc_type"]),
                    chunk_text=text[:1200],
                    summary=text[:280] + ("..." if len(text) > 280 else ""),
                    tags=list(row.get("tags") or []),
                    content_hash=str(row["content_hash"]),
                )
            )

        return RetrieveContextResponse(
            request_id=req.request_id,
            chunks=chunks,
            filters_applied=filters,
            total_candidates=len(rows),
            index_version=self._settings.rag_index_version,
            embedding_model=self._settings.ollama_embed_model,
        )
