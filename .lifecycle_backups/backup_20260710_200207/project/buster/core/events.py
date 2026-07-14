from collections import defaultdict
from typing import Callable

class EventBus:
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, callback: Callable):
        self._listeners[event].append(callback)

    def emit(self, event: str, **payload):
        for callback in list(self._listeners.get(event, [])):
            try:
                callback(**payload)
            except Exception:
                pass
