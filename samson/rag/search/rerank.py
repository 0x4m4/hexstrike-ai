"""Reranking and briefing generation using retrieved chunks."""

from __future__ import annotations

import logging

from samson.core.config import SamsonSettings, get_settings
from samson.core.http_client import OllamaClient
from samson.rag.schemas import BuildBriefRequest, BuildBriefResponse, Citation, ChunkResult

logger = logging.getLogger(__name__)


class ContextReranker:
    def __init__(self, settings: SamsonSettings | None = None, ollama: OllamaClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._ollama = ollama or OllamaClient(self._settings)
        self._owns_ollama = ollama is None

    def close(self) -> None:
        if self._owns_ollama:
            self._ollama.close()

    def rerank(self, query: str, chunks: list[ChunkResult], top_k: int = 8) -> list[ChunkResult]:
        if not chunks:
            return []
        scored: list[tuple[float, ChunkResult]] = []
        query_terms = {t.lower() for t in query.split() if len(t) > 2}
        for chunk in chunks:
            overlap = sum(1 for term in query_terms if term in chunk.chunk_text.lower())
            lexical_boost = overlap / max(len(query_terms), 1)
            fused = (0.75 * chunk.score) + (0.25 * lexical_boost)
            scored.append((fused, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        result: list[ChunkResult] = []
        for fused_score, chunk in scored[:top_k]:
            result.append(chunk.model_copy(update={"score": fused_score}))
        return result

    def build_brief(self, req: BuildBriefRequest) -> BuildBriefResponse:
        chunks = self.rerank(
            query=(req.scenario_draft or {}).get("title", "scenario"),
            chunks=req.retrieve_response.chunks,
            top_k=min(8, len(req.retrieve_response.chunks)),
        )
        citations = [
            Citation(
                chunk_id=c.chunk_id,
                source_path=c.source_path,
                score=c.score,
                excerpt=c.summary,
            )
            for c in chunks
        ]
        context_block = "\n\n".join(
            f"[{c.source_path}] (score={c.score:.3f})\n{c.summary}" for c in chunks
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Samson SBM briefing engine for authorized enterprise red-team audits. "
                    "Produce a concise operator briefing grounded only in supplied context. "
                    "List constraints and cite source paths."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Scenario draft:\n{req.scenario_draft or {}}\n\n"
                    f"Retrieved context:\n{context_block}\n\n"
                    "Return sections: BRIEFING, RELEVANCE, CONSTRAINTS."
                ),
            },
        ]
        raw = self._ollama.chat(messages, temperature=0.1)
        briefing, relevance, constraints = self._parse_sections(raw)
        confidence = sum(c.score for c in chunks) / max(len(chunks), 1)
        return BuildBriefResponse(
            request_id=req.request_id,
            briefing=briefing,
            relevance_rationale=relevance,
            constraints=constraints,
            citations=citations,
            confidence=min(confidence, 1.0),
            index_version=req.retrieve_response.index_version,
            embedding_model=req.retrieve_response.embedding_model,
        )

    @staticmethod
    def _parse_sections(raw: str) -> tuple[str, str, list[str]]:
        sections = {"BRIEFING": "", "RELEVANCE": "", "CONSTRAINTS": ""}
        current = "BRIEFING"
        for line in raw.splitlines():
            upper = line.strip().upper().rstrip(":")
            if upper in sections:
                current = upper
                continue
            sections[current] += line + "\n"
        constraints = [c.strip("- ").strip() for c in sections["CONSTRAINTS"].splitlines() if c.strip()]
        return sections["BRIEFING"].strip(), sections["RELEVANCE"].strip(), constraints
