"""
Conversation persistence: save, load, search, and tag conversations.

Each conversation is stored as a JSON file with metadata (tags, model used,
creation time, etc.) for easy retrieval and categorization.
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from local_ai_studio.chat.engine import ChatMessage


@dataclass
class ConversationMeta:
    """Metadata for a saved conversation."""
    id: str
    title: str
    tags: list[str] = field(default_factory=list)
    mode: str = "general"           # code, research, creative, roleplay, general
    model_name: str = ""
    model_path: str = ""
    message_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    system_prompt: str = ""
    inference_preset: str = ""
    notes: str = ""


@dataclass
class SavedConversation:
    """A full conversation with metadata and messages."""
    meta: ConversationMeta
    messages: list[ChatMessage] = field(default_factory=list)


class ConversationStore:
    """Persists and retrieves conversations as JSON files."""

    def __init__(self, conversations_dir: str):
        self.base_dir = Path(conversations_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        messages: list[ChatMessage],
        title: str = "",
        tags: Optional[list[str]] = None,
        mode: str = "general",
        model_name: str = "",
        model_path: str = "",
        system_prompt: str = "",
        inference_preset: str = "",
        conversation_id: Optional[str] = None,
        notes: str = "",
    ) -> str:
        """Save a conversation. Returns the conversation ID."""
        conv_id = conversation_id or str(uuid.uuid4())[:12]
        now = time.time()

        meta = ConversationMeta(
            id=conv_id,
            title=title or self._auto_title(messages),
            tags=tags or [],
            mode=mode,
            model_name=model_name,
            model_path=model_path,
            message_count=len(messages),
            created_at=now if not conversation_id else self._get_created(conv_id, now),
            updated_at=now,
            system_prompt=system_prompt,
            inference_preset=inference_preset,
            notes=notes,
        )

        data = {
            "meta": asdict(meta),
            "messages": [m.to_dict() for m in messages],
        }

        filepath = self.base_dir / f"{conv_id}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return conv_id

    def load(self, conversation_id: str) -> Optional[SavedConversation]:
        """Load a conversation by ID."""
        filepath = self.base_dir / f"{conversation_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath) as f:
                data = json.load(f)
            meta = ConversationMeta(**data["meta"])
            messages = [ChatMessage.from_dict(m) for m in data["messages"]]
            return SavedConversation(meta=meta, messages=messages)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def list_conversations(
        self,
        tag: Optional[str] = None,
        mode: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> list[ConversationMeta]:
        """List conversations with optional filtering."""
        results: list[ConversationMeta] = []
        for filepath in sorted(self.base_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                meta = ConversationMeta(**data["meta"])
            except (json.JSONDecodeError, KeyError, TypeError, OSError):
                continue

            if tag and tag not in meta.tags:
                continue
            if mode and meta.mode != mode:
                continue
            if search and search.lower() not in meta.title.lower():
                # Also search in notes
                if search.lower() not in meta.notes.lower():
                    continue

            results.append(meta)
            if len(results) >= limit:
                break

        # Sort by updated_at descending
        results.sort(key=lambda m: m.updated_at, reverse=True)
        return results

    def delete(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        filepath = self.base_dir / f"{conversation_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def update_tags(self, conversation_id: str, tags: list[str]) -> bool:
        """Update tags on an existing conversation."""
        conv = self.load(conversation_id)
        if conv is None:
            return False
        conv.meta.tags = tags
        conv.meta.updated_at = time.time()
        self._write(conv)
        return True

    def get_all_tags(self) -> list[str]:
        """Get all unique tags across all conversations."""
        tags: set[str] = set()
        for filepath in self.base_dir.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                for t in data.get("meta", {}).get("tags", []):
                    tags.add(t)
            except (json.JSONDecodeError, OSError):
                continue
        return sorted(tags)

    def export_conversation(self, conversation_id: str, format: str = "json") -> Optional[str]:
        """Export a conversation as formatted text.

        format: 'json' returns raw JSON, 'markdown' returns formatted MD.
        """
        conv = self.load(conversation_id)
        if conv is None:
            return None

        if format == "json":
            return json.dumps(
                {"meta": asdict(conv.meta), "messages": [m.to_dict() for m in conv.messages]},
                indent=2,
            )
        elif format == "markdown":
            lines = [f"# {conv.meta.title}\n"]
            lines.append(f"**Mode**: {conv.meta.mode} | **Model**: {conv.meta.model_name}")
            lines.append(f"**Tags**: {', '.join(conv.meta.tags)}\n")
            lines.append("---\n")
            for msg in conv.messages:
                if msg.role == "system":
                    lines.append(f"*System: {msg.content}*\n")
                elif msg.role == "user":
                    lines.append(f"**User**: {msg.content}\n")
                elif msg.role == "assistant":
                    lines.append(f"**Assistant**: {msg.content}\n")
                elif msg.role == "tool":
                    lines.append(f"> Tool ({msg.tool_name}): {msg.content}\n")
            return "\n".join(lines)
        return None

    # -- internals -----------------------------------------------------------

    def _write(self, conv: SavedConversation) -> None:
        data = {
            "meta": asdict(conv.meta),
            "messages": [m.to_dict() for m in conv.messages],
        }
        filepath = self.base_dir / f"{conv.meta.id}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _get_created(self, conv_id: str, fallback: float) -> float:
        filepath = self.base_dir / f"{conv_id}.json"
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                return data["meta"]["created_at"]
            except (json.JSONDecodeError, KeyError, OSError):
                pass
        return fallback

    @staticmethod
    def _auto_title(messages: list[ChatMessage]) -> str:
        for m in messages:
            if m.role == "user" and m.content.strip():
                title = m.content.strip()[:80]
                if len(m.content.strip()) > 80:
                    title += "..."
                return title
        return f"Conversation {time.strftime('%Y-%m-%d %H:%M')}"
