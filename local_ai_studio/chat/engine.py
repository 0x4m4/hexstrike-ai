"""
Chat engine: orchestrates conversations with the loaded model.

Manages message formatting, system prompts, tool invocations within
a conversation turn, and streaming output.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from local_ai_studio.config import StudioConfig
from local_ai_studio.models.manager import ModelLoader


@dataclass
class ChatMessage:
    """A single message in a conversation."""
    role: str               # "system", "user", "assistant", "tool"
    content: str
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    # For tool calls
    tool_name: Optional[str] = None
    tool_input: Optional[str] = None
    tool_output: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        if self.tool_name:
            d["tool_name"] = self.tool_name
            d["tool_input"] = self.tool_input
            d["tool_output"] = self.tool_output
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ChatMessage":
        return cls(
            role=d["role"],
            content=d["content"],
            timestamp=d.get("timestamp", 0.0),
            metadata=d.get("metadata", {}),
            tool_name=d.get("tool_name"),
            tool_input=d.get("tool_input"),
            tool_output=d.get("tool_output"),
        )


class ChatEngine:
    """Drives multi-turn conversations with context management."""

    def __init__(self, config: StudioConfig, model_loader: ModelLoader):
        self.config = config
        self.loader = model_loader
        self.messages: list[ChatMessage] = []
        self._system_prompt: str = ""
        self._tool_executor = None  # set externally by the app

    # -- public API ----------------------------------------------------------

    def set_system_prompt(self, prompt: str) -> None:
        """Set (or replace) the system prompt for this session."""
        self._system_prompt = prompt
        # Replace or insert the system message at position 0
        if self.messages and self.messages[0].role == "system":
            self.messages[0].content = prompt
        else:
            self.messages.insert(
                0,
                ChatMessage(role="system", content=prompt, timestamp=time.time()),
            )

    def set_tool_executor(self, executor) -> None:
        """Attach a ToolExecutor for automatic tool invocations."""
        self._tool_executor = executor

    def send(
        self,
        user_input: str,
        stream: bool = True,
        **kwargs,
    ) -> Generator[str, None, None] | str:
        """Send a user message and get the assistant response.

        In streaming mode, yields partial tokens. Otherwise returns full text.
        """
        # Ensure system prompt is present
        if not any(m.role == "system" for m in self.messages):
            sys_prompt = self._system_prompt or self.config.get_system_prompt()
            self.messages.insert(
                0,
                ChatMessage(role="system", content=sys_prompt, timestamp=time.time()),
            )

        # Add user message
        self.messages.append(
            ChatMessage(role="user", content=user_input, timestamp=time.time())
        )

        # Build messages list for the model (trim to context window)
        model_messages = self._build_context_window()

        if stream:
            return self._stream_response(model_messages, **kwargs)
        else:
            return self._full_response(model_messages, **kwargs)

    def get_messages(self) -> list[ChatMessage]:
        """Return all messages in the current conversation."""
        return list(self.messages)

    def clear(self) -> None:
        """Clear conversation history (keeps system prompt)."""
        sys = None
        if self.messages and self.messages[0].role == "system":
            sys = self.messages[0]
        self.messages.clear()
        if sys:
            self.messages.append(sys)

    def set_messages(self, messages: list[ChatMessage]) -> None:
        """Restore a conversation from saved messages."""
        self.messages = messages

    def trim_context(self, max_messages: Optional[int] = None) -> None:
        """Trim old messages to stay within context limits.

        Keeps the system prompt and the most recent messages.
        """
        if max_messages is None:
            max_messages = 100  # sensible default
        if len(self.messages) <= max_messages:
            return
        system = [m for m in self.messages if m.role == "system"]
        rest = [m for m in self.messages if m.role != "system"]
        self.messages = system + rest[-(max_messages - len(system)):]

    # -- internals -----------------------------------------------------------

    def _build_context_window(self) -> list[dict[str, str]]:
        """Convert internal messages to the format expected by the model backend."""
        context_length = self.config.get("inference.context_length", 8192)
        # Rough heuristic: 4 chars per token, leave room for response
        max_chars = context_length * 4 - self.config.get("inference.max_tokens", 4096) * 4

        result = []
        total_chars = 0

        # Always include system prompt first
        for m in self.messages:
            if m.role == "system":
                result.append({"role": "system", "content": m.content})
                total_chars += len(m.content)
                break

        # Add recent messages, newest first, then reverse
        recent = [m for m in self.messages if m.role != "system"]
        selected = []
        for m in reversed(recent):
            msg_chars = len(m.content)
            if total_chars + msg_chars > max_chars and selected:
                break
            selected.append({"role": m.role, "content": m.content})
            total_chars += msg_chars

        selected.reverse()
        result.extend(selected)
        return result

    def _stream_response(
        self, messages: list[dict[str, str]], **kwargs
    ) -> Generator[str, None, None]:
        gen = self.loader.chat_completion(messages, stream=True, **kwargs)
        full_response = []
        for token in gen:
            full_response.append(token)
            yield token
        # Save assistant message
        self.messages.append(
            ChatMessage(
                role="assistant",
                content="".join(full_response),
                timestamp=time.time(),
            )
        )

    def _full_response(self, messages: list[dict[str, str]], **kwargs) -> str:
        result = self.loader.chat_completion(messages, stream=False, **kwargs)
        self.messages.append(
            ChatMessage(role="assistant", content=result, timestamp=time.time())
        )
        return result
