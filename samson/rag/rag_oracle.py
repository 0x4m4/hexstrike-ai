"""RAG Oracle service — retrieve_context, build_brief, write_report_context (ADR-002)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.http_client import OllamaClient
from samson.core.scope import ScopeEnforcer
from samson.rag.schemas import (
    BuildBriefRequest,
    BuildBriefResponse,
    ChunkResult,
    Citation,
    RetrieveContextRequest,
    RetrieveContextResponse,
    TimelineEvent,
    WriteReportContextRequest,
    WriteReportContextResponse,
)
from samson.rag.search.ingest import DocumentIngester
from samson.rag.search.rerank import ContextReranker
from samson.rag.search.retrieve import ContextRetriever

logger = logging.getLogger(__name__)


class RagOracle:
    """Orchestrator-facing RAG service with audit logging and citation-first outputs."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._scope = ScopeEnforcer(self._settings)
        self._ollama = OllamaClient(self._settings)
        self._retriever = ContextRetriever(self._settings, self._db, self._ollama, self._scope)
        self._reranker = ContextReranker(self._settings, self._ollama)
        self._ingester = DocumentIngester(self._settings, self._db, self._ollama, self._scope)

    def close(self) -> None:
        self._ingester.close()
        self._retriever.close()
        self._reranker.close()
        self._ollama.close()

    def retrieve_context(self, req: RetrieveContextRequest) -> RetrieveContextResponse:
        start = time.perf_counter()
        response = self._retriever.retrieve(req)
        response.chunks = self._reranker.rerank(req.query, response.chunks, top_k=req.top_k)
        duration_ms = int((time.perf_counter() - start) * 1000)
        if self._settings.audit_enabled:
            self._audit.write_rag_audit(
                request_id=req.request_id,
                mode="retrieve_context",
                operator_id=req.operator_id,
                project=req.project,
                environment=req.environment,
                query_hash=sha256_payload(req.model_dump(mode="json")),
                chunks_returned=len(response.chunks),
                index_version=response.index_version,
                embedding_model=response.embedding_model,
                duration_ms=duration_ms,
            )
        return response

    def build_brief(self, req: BuildBriefRequest) -> BuildBriefResponse:
        start = time.perf_counter()
        response = self._reranker.build_brief(req)
        duration_ms = int((time.perf_counter() - start) * 1000)
        if self._settings.audit_enabled:
            self._audit.write_rag_audit(
                request_id=req.request_id,
                mode="build_brief",
                operator_id=None,
                project=self._settings.project,
                environment=self._settings.environment,
                query_hash=sha256_payload(req.model_dump(mode="json")),
                chunks_returned=len(response.citations),
                index_version=response.index_version,
                embedding_model=response.embedding_model,
                duration_ms=duration_ms,
            )
        return response

    def write_report_context(self, req: WriteReportContextRequest) -> WriteReportContextResponse:
        start = time.perf_counter()
        self._scope.assert_operator(req.operator_id, request_id=req.request_id)

        report_id = uuid4()
        reports_dir = self._settings.rag_reports_path
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{report_id}.md"
        sidecar_path = reports_dir / f"{report_id}.json"

        remediation_query = " ".join(req.remediation_notes) or "remediation playbook guardrail"
        retrieval = self.retrieve_context(
            RetrieveContextRequest(
                request_id=uuid4(),
                query=remediation_query,
                environment=self._settings.environment,
                project=self._settings.project,
                operator_id=req.operator_id,
                tags=["playbook", "runbook", "remediation"],
                top_k=6,
            )
        )
        remediation_refs = retrieval.chunks

        timeline = [
            TimelineEvent(
                timestamp=datetime.now(tz=timezone.utc),
                event_type="report_generated",
                description=f"Exercise report for scenario {req.scenario_id}",
                reference_id=str(req.run_id),
            )
        ]
        for finding in req.findings:
            timeline.append(
                TimelineEvent(
                    timestamp=datetime.now(tz=timezone.utc),
                    event_type="finding",
                    description=f"[{finding.severity}] {finding.description}",
                    reference_id=finding.finding_id,
                )
            )

        citations = [
            {
                "chunk_id": str(c.chunk_id),
                "source_path": c.source_path,
                "score": c.score,
                "excerpt": c.summary,
            }
            for c in remediation_refs
        ]

        markdown = self._render_report_markdown(req, remediation_refs, timeline)
        report_path.write_text(markdown, encoding="utf-8")
        sidecar = {
            "report_id": str(report_id),
            "run_id": str(req.run_id),
            "scenario_id": req.scenario_id,
            "operator_id": req.operator_id,
            "telemetry_summary": req.telemetry_summary,
            "findings": [f.model_dump(mode="json") for f in req.findings],
            "citations": citations,
            "timeline": [t.model_dump(mode="json") for t in timeline],
        }
        sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")

        self._ingester.ingest_path(
            report_path,
            doc_type="report",
            project=self._settings.project,
            environment=self._settings.environment,
            tags=["exercise_report", req.scenario_id],
        )

        duration_ms = int((time.perf_counter() - start) * 1000)
        if self._settings.audit_enabled:
            self._audit.write_rag_audit(
                request_id=req.request_id,
                mode="write_report_context",
                operator_id=req.operator_id,
                project=self._settings.project,
                environment=self._settings.environment,
                query_hash=sha256_payload(req.model_dump(mode="json")),
                chunks_returned=len(remediation_refs),
                index_version=self._settings.rag_index_version,
                embedding_model=self._settings.ollama_embed_model,
                duration_ms=duration_ms,
            )

        return WriteReportContextResponse(
            request_id=req.request_id,
            report_id=report_id,
            report_path=str(report_path),
            citations=[
                Citation(
                    chunk_id=c.chunk_id,
                    source_path=c.source_path,
                    score=c.score,
                    excerpt=c.summary,
                )
                for c in remediation_refs
            ],
            remediation_references=remediation_refs,
            timeline=timeline,
        )

    @staticmethod
    def _render_report_markdown(
        req: WriteReportContextRequest,
        remediation_refs: list[ChunkResult],
        timeline: list[TimelineEvent],
    ) -> str:
        lines = [
            f"# Samson SBM Exercise Report",
            "",
            f"- **Run ID:** `{req.run_id}`",
            f"- **Scenario:** `{req.scenario_id}`",
            f"- **Operator:** `{req.operator_id}`",
            "",
            "## Telemetry Summary",
            "```json",
            json.dumps(req.telemetry_summary, indent=2),
            "```",
            "",
            "## Findings",
        ]
        if not req.findings:
            lines.append("_No findings recorded._")
        else:
            for f in req.findings:
                lines.append(f"- **[{f.severity}]** {f.description}")
                if f.evidence:
                    lines.append(f"  - Evidence: {f.evidence[:500]}")
        lines.extend(["", "## Remediation References"])
        for ref in remediation_refs:
            lines.append(f"- `{ref.source_path}` (score={ref.score:.3f})")
        lines.extend(["", "## Timeline"])
        for event in timeline:
            lines.append(f"- `{event.timestamp.isoformat()}` **{event.event_type}**: {event.description}")
        return "\n".join(lines) + "\n"
