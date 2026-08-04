"""dedup_engine — pattern-based alert filtering (15-minute window)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from hexstrike.bus.context_bus import ContextBus


def _pair_key(frm: str, to: str) -> str:
    return f"{(frm or '').lower()}:{(to or '').lower()}"


@dataclass
class DedupEngine:
    """Suppress repeated from+to alert patterns within a configurable window."""

    bus: ContextBus
    window_seconds: int = 15 * 60
    _pairs: dict[str, float] = field(default_factory=dict)

    def prune(self) -> None:
        cutoff = time.time() - self.window_seconds
        self._pairs = {k: ts for k, ts in self._pairs.items() if ts >= cutoff}

    def is_duplicate(self, frm: str, to: str) -> bool:
        self.prune()
        key = _pair_key(frm, to)
        last = self._pairs.get(key)
        if last is None:
            return False
        return (time.time() - last) < self.window_seconds

    def record(self, frm: str, to: str) -> None:
        self.prune()
        key = _pair_key(frm, to)
        self._pairs[key] = time.time()
        self.bus.publish(
            "skill.dedup.recorded",
            {"pair": key, "window_sec": self.window_seconds},
            source="dedup_engine",
        )

    def filter_alert(self, alert: dict[str, Any]) -> dict[str, Any] | None:
        frm = alert.get("from", "")
        to = alert.get("to", "")
        if self.is_duplicate(frm, to):
            self.bus.publish(
                "skill.dedup.suppressed",
                {"from": frm, "to": to, "hash": alert.get("hash")},
                source="dedup_engine",
            )
            return None
        self.record(frm, to)
        return alert

    def snapshot(self) -> dict[str, Any]:
        self.prune()
        return {"active_pairs": len(self._pairs), "window_seconds": self.window_seconds}
