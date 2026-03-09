"""
Tool executor: dispatches tool calls to the appropriate handler.

Provides a unified interface for the chat engine to invoke tools and
collects results. Enforces permission checks from configuration.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from local_ai_studio.config import StudioConfig

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a single tool invocation."""
    name: str
    input: dict[str, Any]
    output: str = ""
    success: bool = False
    duration_ms: float = 0.0
    timestamp: float = 0.0
    error: str = ""


@dataclass
class ToolDefinition:
    """Describes a tool available to the AI."""
    name: str
    description: str
    parameters: dict[str, Any]      # JSON Schema for inputs
    handler: Callable
    category: str = "general"       # python, filesystem, web, database, git, shell
    requires_confirmation: bool = False


class ToolExecutor:
    """Central registry and executor for all tools."""

    def __init__(self, config: StudioConfig):
        self.config = config
        self._tools: dict[str, ToolDefinition] = {}
        self._history: list[ToolCall] = []
        self._max_history = 1000

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        self._tools.pop(name, None)

    def list_tools(self) -> list[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return tool schemas in OpenAI function-calling format."""
        schemas = []
        for tool in self._tools.values():
            if not self._is_enabled(tool):
                continue
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return schemas

    def execute(self, name: str, inputs: dict[str, Any]) -> ToolCall:
        """Execute a tool by name with the given inputs."""
        call = ToolCall(name=name, input=inputs, timestamp=time.time())

        tool = self._tools.get(name)
        if tool is None:
            call.error = f"Unknown tool: {name}"
            call.success = False
            self._record(call)
            return call

        if not self._is_enabled(tool):
            call.error = f"Tool '{name}' is disabled in configuration"
            call.success = False
            self._record(call)
            return call

        start = time.monotonic()
        try:
            result = tool.handler(**inputs)
            call.output = str(result) if result is not None else ""
            call.success = True
        except Exception as e:
            call.error = f"{type(e).__name__}: {e}"
            call.success = False
            logger.exception("Tool execution failed: %s", name)
        finally:
            call.duration_ms = (time.monotonic() - start) * 1000

        self._record(call)
        return call

    def get_history(self, limit: int = 50) -> list[ToolCall]:
        """Return recent tool call history."""
        return list(reversed(self._history[-limit:]))

    def clear_history(self) -> None:
        self._history.clear()

    # -- internals -----------------------------------------------------------

    def _is_enabled(self, tool: ToolDefinition) -> bool:
        """Check if a tool's category is enabled in config."""
        category_map = {
            "python": "tools.python_sandbox.enabled",
            "filesystem": "tools.filesystem.enabled",
            "web": "tools.web.enabled",
            "database": "tools.database.enabled",
            "git": "tools.git.enabled",
            "shell": "tools.shell.enabled",
        }
        config_key = category_map.get(tool.category)
        if config_key is None:
            return True  # Unknown categories default to enabled
        return self.config.get(config_key, True)

    def _record(self, call: ToolCall) -> None:
        """Record a tool call in history."""
        self._history.append(call)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        if self.config.get("logging.log_tool_calls", True):
            status = "OK" if call.success else f"FAIL: {call.error}"
            logger.info(
                "Tool call: %s (%.0fms) - %s",
                call.name, call.duration_ms, status,
            )
