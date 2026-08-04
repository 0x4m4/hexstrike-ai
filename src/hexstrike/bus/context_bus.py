"""ContextBus — lightweight pub/sub for HexStrike modules and skills."""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class Event:
    topic: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    source: str = "unknown"


Handler = Callable[[Event], None]


class ContextBus:
    """Thread-safe in-process event bus shared by orchestrator, core modules, and MCPs."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._history: list[Event] = []
        self._lock = threading.RLock()
        self._max_history = 500

    def subscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            self._handlers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            if handler in self._handlers.get(topic, []):
                self._handlers[topic].remove(handler)

    def publish(self, topic: str, payload: dict[str, Any], *, source: str = "unknown") -> Event:
        event = Event(topic=topic, payload=payload, source=source)
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]
            handlers = list(self._handlers.get(topic, [])) + list(self._handlers.get("*", []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 — bus must not crash publishers
                print(f"[ContextBus] handler error on {topic}: {exc}")
        return event

    def recent(self, topic: str | None = None, limit: int = 50) -> list[Event]:
        with self._lock:
            events = self._history if topic is None else [e for e in self._history if e.topic == topic]
        return events[-limit:]

    def wait_for(self, topic: str, timeout: float = 30.0) -> Event | None:
        result: list[Event] = []
        done = threading.Event()

        def _capture(event: Event) -> None:
            result.append(event)
            done.set()

        self.subscribe(topic, _capture)
        try:
            if done.wait(timeout):
                return result[0]
            return None
        finally:
            self.unsubscribe(topic, _capture)
