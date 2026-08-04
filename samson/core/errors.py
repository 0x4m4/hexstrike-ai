"""Samson exception hierarchy with structured error payloads for audit and API surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class ErrorDetail:
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


class SamsonError(Exception):
    """Base error for all Samson SBM operations."""

    def __init__(self, message: str, *, code: str = "samson_error", context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.detail = ErrorDetail(code=code, message=message, context=context or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.detail.code,
            "message": self.detail.message,
            "context": self.detail.context,
        }


class ConfigurationError(SamsonError):
    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message, code="configuration_error", context=context)


class DatabaseError(SamsonError):
    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message, code="database_error", context=context)


class NetworkError(SamsonError):
    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message, code="network_error", context=context)


class ScopeViolationError(SamsonError):
    def __init__(self, message: str, *, request_id: UUID | None = None, **context: Any) -> None:
        ctx = dict(context)
        if request_id is not None:
            ctx["request_id"] = str(request_id)
        super().__init__(message, code="scope_violation", context=ctx)


class ApprovalRequiredError(SamsonError):
    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message, code="approval_required", context=context)


class ToolExecutionError(SamsonError):
    def __init__(self, tool: str, message: str, **context: Any) -> None:
        super().__init__(message, code="tool_execution_error", context={"tool": tool, **context})


class EmbeddingError(SamsonError):
    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message, code="embedding_error", context=context)


class PayloadOrchestrationError(SamsonError):
    def __init__(self, message: str, *, payload_id: str | None = None, **context: Any) -> None:
        ctx = dict(context)
        if payload_id is not None:
            ctx["payload_id"] = payload_id
        super().__init__(message, code="payload_orchestration_error", context=ctx)
