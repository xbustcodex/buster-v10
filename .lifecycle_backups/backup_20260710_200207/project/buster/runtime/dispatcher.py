from __future__ import annotations
from typing import Any, Callable, Dict, List
from .storage import append_json, now
from pathlib import Path
EVENTS_PATH = Path('data/runtime_events.json')
class RuntimeDispatcher:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}
    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self.subscribers.setdefault(event_type, []).append(handler)
    def publish(self, event_type: str, payload: Dict[str, Any] | None = None, source: str = 'runtime') -> Dict[str, Any]:
        event={'type': event_type, 'source': source, 'payload': payload or {}, 'created_at': now()}
        append_json(EVENTS_PATH, event, limit=1000)
        for handler in self.subscribers.get(event_type, []) + self.subscribers.get('*', []):
            try: handler(event)
            except Exception: pass
        return event
