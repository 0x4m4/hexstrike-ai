"""Pydantic schemas for Samson RAG Oracle (ADR-002)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkResult(BaseModel):
    chunk_id: UUID
    doc_id: UUID
    score: float
    source_path: str
    doc_type: str
    chunk_text: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    content_hash: str


class RetrieveContextRequest(BaseModel):
    request_id: UUID
    query: str
    scenario_type: str | None = None
    target_profile: dict | None = None
    tags: list[str] = Field(default_factory=list)
    environment: Literal["dev", "stage", "prod"]
    project: str
    top_k: int = Field(default=8, ge=1, le=32)
    operator_id: str


class RetrieveContextResponse(BaseModel):
    request_id: UUID
    chunks: list[ChunkResult]
    filters_applied: dict
    total_candidates: int
    index_version: int
    embedding_model: str


class Citation(BaseModel):
    chunk_id: UUID
    source_path: str
    score: float
    excerpt: str


class BuildBriefRequest(BaseModel):
    request_id: UUID
    retrieve_response: RetrieveContextResponse
    scenario_draft: dict | None = None


class BuildBriefResponse(BaseModel):
    request_id: UUID
    briefing: str
    relevance_rationale: str
    constraints: list[str]
    citations: list[Citation]
    confidence: float
    index_version: int
    embedding_model: str


class Finding(BaseModel):
    finding_id: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    description: str
    evidence: str


class TimelineEvent(BaseModel):
    timestamp: datetime
    event_type: str
    description: str
    reference_id: str | None = None


class WriteReportContextRequest(BaseModel):
    request_id: UUID
    run_id: UUID
    operator_id: str
    scenario_id: str
    telemetry_summary: dict
    findings: list[Finding] = Field(default_factory=list)
    remediation_notes: list[str] = Field(default_factory=list)


class WriteReportContextResponse(BaseModel):
    request_id: UUID
    report_id: UUID
    report_path: str
    citations: list[Citation]
    remediation_references: list[ChunkResult]
    timeline: list[TimelineEvent]
