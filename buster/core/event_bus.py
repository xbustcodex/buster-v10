from buster.utils.datetime_utils import utc_now, utc_timestamp

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List


@dataclass
class Event:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "buster"
    timestamp: str = field(default_factory=lambda: utc_now().replace(tzinfo=None).isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "payload": self.payload, "source": self.source, "timestamp": self.timestamp}


Subscriber = Callable[[Event], None]


class EventBus:
    def __init__(self, history_path: str | Path = "data/event_history.json") -> None:
        self.subscribers: Dict[str, List[Subscriber]] = {}
        self.history_path = Path(history_path)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            self.history_path.write_text("[]", encoding="utf-8")

    def subscribe(self, event_type: str, callback: Subscriber) -> None:
        self.subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event_type: str, payload: Dict[str, Any] | None = None, source: str = "buster") -> Event:
        event = Event(event_type, payload or {}, source)
        self._append_history(event)
        for callback in self.subscribers.get(event_type, []):
            callback(event)
        for callback in self.subscribers.get("*", []):
            callback(event)
        return event

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            items = json.loads(self.history_path.read_text(encoding="utf-8"))
        except Exception:
            items = []
        return items[-limit:]

    def _append_history(self, event: Event) -> None:
        try:
            items = json.loads(self.history_path.read_text(encoding="utf-8"))
            if not isinstance(items, list):
                items = []
        except Exception:
            items = []
        items.append(event.to_dict())
        self.history_path.write_text(json.dumps(items[-500:], indent=2), encoding="utf-8")

# --- NEW EXTENSIONS (APPENDED TO ORIGINAL FILE) ---
# Authoritative shared instance deployment
main_event_bus = EventBus()