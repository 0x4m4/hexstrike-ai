"""PostgreSQL persistence with connection pooling and pgvector-ready operations."""

from __future__ import annotations

import hashlib
import json
import logging
from contextlib import contextmanager
from typing import Any, Generator, Iterable, Sequence
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from samson.core.config import SamsonSettings, get_settings
from samson.core.errors import DatabaseError

logger = logging.getLogger(__name__)


class Database:
    """SQLAlchemy engine wrapper for Samson SBM."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._engine: Engine = create_engine(
            self._settings.database_url,
            pool_size=self._settings.db_pool_size,
            max_overflow=self._settings.db_max_overflow,
            pool_timeout=self._settings.db_pool_timeout_sec,
            pool_pre_ping=True,
            future=True,
        )
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    @property
    def engine(self) -> Engine:
        return self._engine

    @contextmanager
    def connection(self) -> Generator[Connection, None, None]:
        conn = self._engine.connect()
        try:
            yield conn
            conn.commit()
        except SQLAlchemyError as exc:
            conn.rollback()
            raise DatabaseError("Database operation failed", error=str(exc)) from exc
        finally:
            conn.close()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise DatabaseError("Database session failed", error=str(exc)) from exc
        finally:
            session.close()

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        with self.connection() as conn:
            conn.execute(text(sql), params or {})

    def fetchall(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.connection() as conn:
            result = conn.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result.fetchall()]

    def fetchone(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        rows = self.fetchall(sql, params)
        return rows[0] if rows else None

    def ensure_schema(self, migration_paths: Iterable[str]) -> None:
        for path in migration_paths:
            sql = open(path, encoding="utf-8").read()
            logger.info("Applying migration: %s", path)
            self.execute(sql)

    def health_check(self) -> dict[str, Any]:
        row = self.fetchone("SELECT 1 AS ok")
        return {"ok": bool(row and row.get("ok") == 1)}


def vector_literal(values: Sequence[float]) -> str:
    """Format embedding vector for pgvector SQL literal."""
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


class AuditRepository:
    """Append-only audit writers for RAG and red team operations."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def write_rag_audit(
        self,
        *,
        request_id: UUID,
        mode: str,
        operator_id: str | None,
        project: str,
        environment: str,
        query_hash: str,
        chunks_returned: int,
        index_version: int,
        embedding_model: str,
        duration_ms: int,
    ) -> UUID:
        audit_id = uuid4()
        self._db.execute(
            """
            INSERT INTO rag_audit_log (
                audit_id, request_id, mode, operator_id, project, environment,
                query_hash, chunks_returned, index_version, embedding_model, duration_ms
            ) VALUES (
                :audit_id, :request_id, :mode, :operator_id, :project, :environment,
                :query_hash, :chunks_returned, :index_version, :embedding_model, :duration_ms
            )
            """,
            {
                "audit_id": str(audit_id),
                "request_id": str(request_id),
                "mode": mode,
                "operator_id": operator_id,
                "project": project,
                "environment": environment,
                "query_hash": query_hash,
                "chunks_returned": chunks_returned,
                "index_version": index_version,
                "embedding_model": embedding_model,
                "duration_ms": duration_ms,
            },
        )
        return audit_id

    def write_redteam_audit(
        self,
        *,
        request_id: UUID,
        tool: str,
        operator_id: str | None,
        action: str,
        outcome: str,
        payload_hash: str,
        duration_ms: int,
        run_id: UUID | None = None,
    ) -> UUID:
        audit_id = uuid4()
        self._db.execute(
            """
            INSERT INTO redteam_audit_log (
                audit_id, request_id, tool, operator_id, action, outcome,
                payload_hash, duration_ms, run_id
            ) VALUES (
                :audit_id, :request_id, :tool, :operator_id, :action, :outcome,
                :payload_hash, :duration_ms, :run_id
            )
            """,
            {
                "audit_id": str(audit_id),
                "request_id": str(request_id),
                "tool": tool,
                "operator_id": operator_id,
                "action": action,
                "outcome": outcome,
                "payload_hash": payload_hash,
                "duration_ms": duration_ms,
                "run_id": str(run_id) if run_id else None,
            },
        )
        return audit_id
