from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Dict, List
import uuid


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Event:
    type: str
    source: str = "buster"
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=now_utc)


class UnifiedEventAPI:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self.history: List[Event] = []

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any] | None = None,
        source: str = "buster",
        priority: EventPriority | str = EventPriority.NORMAL,
    ) -> Event:
        if isinstance(priority, str):
            priority = EventPriority(priority)
        event = Event(type=event_type, source=source, payload=payload or {}, priority=priority)
        self.history.append(event)

        for handler in self._subscribers.get(event_type, []):
            handler(event)
        for handler in self._subscribers.get("*", []):
            handler(event)

        return event

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "type": e.type,
                "source": e.source,
                "priority": e.priority.value,
                "payload": e.payload,
            }
            for e in self.history[-limit:]
        ]
