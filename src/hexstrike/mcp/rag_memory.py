"""mcp_rag_memory — LanceDB interface for historical pattern retrieval."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from rag_core import (  # noqa: E402
    RagStorageError,
    index_false_positive,
    is_false_positive_pattern,
    search_history,
)


@dataclass
class RagMemoryMcp:
    """LanceDB-backed forensic memory for agents."""

    bus: ContextBus

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        try:
            hits = search_history(query, top_k=top_k)
            self.bus.publish(
                "mcp.rag.search",
                {"query": query[:120], "hits": len(hits)},
                source="mcp_rag_memory",
            )
            return hits
        except (RagStorageError, OSError, ImportError) as exc:
            self.bus.publish("mcp.rag.error", {"error": str(exc)}, source="mcp_rag_memory")
            return []

    def is_false_positive(self, tx_hash: str, frm: str, to: str) -> tuple[bool, list]:
        try:
            match, hits = is_false_positive_pattern(tx_hash, frm, to)
            return match, hits
        except (RagStorageError, OSError, ImportError):
            return False, []

    def index_feedback(self, tx_hash: str, frm: str, to: str, note: str = "") -> dict[str, Any]:
        try:
            index_false_positive(tx_hash, frm, to, note)
            self.bus.publish("mcp.rag.feedback_indexed", {"tx_hash": tx_hash}, source="mcp_rag_memory")
            return {"success": True}
        except (RagStorageError, OSError, ImportError) as exc:
            return {"success": False, "error": str(exc)}
