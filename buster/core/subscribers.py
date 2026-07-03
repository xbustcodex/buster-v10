from __future__ import annotations

from typing import Any, Dict, List
from .event_bus import Event
from .event_types import EventTypes


class EventRecorder:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event.to_dict())


def register_default_subscribers(bus) -> EventRecorder:
    recorder = EventRecorder()
    bus.subscribe("*", recorder)
    return recorder


def publish_system_started(bus) -> None:
    bus.publish(EventTypes.SYSTEM_STARTED, {"status": "ready"}, source="core")
