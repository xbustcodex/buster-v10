from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class TimelineEvent:
    source: str
    message: str
    level: str = "info"
    mission_id: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "mission_id": self.mission_id,
            "source": self.source,
            "message": self.message,
            "level": self.level,
            "metadata": self.metadata,
        }


class ActivityTimeline:
    def __init__(self, path: str | Path = "data/mission_timeline_live.json", limit: int = 500):
        self.path = Path(path)
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write(self, events: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(events[-self.limit:], indent=2), encoding="utf-8")

    def add(self, source: str, message: str, level: str = "info", mission_id: str = "default", **metadata: Any) -> Dict[str, Any]:
        event = TimelineEvent(
            source=source,
            message=message,
            level=level,
            mission_id=mission_id,
            metadata=metadata,
        ).to_dict()
        events = self._read()
        events.append(event)
        self._write(events)
        return event

    def list_recent(self, count: int = 20) -> List[Dict[str, Any]]:
        return self._read()[-count:]

    def clear(self) -> None:
        self._write([])
