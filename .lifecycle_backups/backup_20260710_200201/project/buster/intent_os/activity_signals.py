from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List
import uuid


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class ActivitySignal:
    source: str
    type: str
    summary: str
    confidence: float = 0.7
    importance: float = 0.6
    data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=now_utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "source": self.source,
            "type": self.type,
            "summary": self.summary,
            "confidence": self.confidence,
            "importance": self.importance,
            "data": self.data,
        }


class ActivitySignalBuffer:
    def __init__(self, max_items: int = 200) -> None:
        self.max_items = max_items
        self.signals: List[ActivitySignal] = []

    def add(self, signal: ActivitySignal) -> ActivitySignal:
        self.signals.append(signal)
        self.signals = self.signals[-self.max_items:]
        return signal

    def extend(self, signals: List[ActivitySignal]) -> None:
        for signal in signals:
            self.add(signal)

    def recent(self, limit: int = 50) -> List[ActivitySignal]:
        return self.signals[-limit:]

    def as_text(self) -> str:
        parts = []
        for signal in self.recent():
            parts.append(signal.summary)
            parts.extend(str(v) for v in signal.data.values())
        return " ".join(parts).lower()
