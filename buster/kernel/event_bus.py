"""
Unified Event Bus for Buster Kernel v10.5
Provides async and synchronous pub/sub event routing across system modules.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("buster.kernel.event_bus")


@dataclass
class Event:
    """Core Event payload representation."""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Central Event Bus for decoupled communication between Kernel services."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable[[Event], Any]]] = {}
        self._history: List[Event] = []
        self._max_history: int = 500

    def subscribe(self, event_name: str, callback: Callable[[Event], Any]) -> None:
        """Register a callback for a specific event type."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        if callback not in self._listeners[event_name]:
            self._listeners[event_name].append(callback)
            logger.debug(f"Subscribed {callback.__name__} to event: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable[[Event], Any]) -> None:
        """Remove a callback from an event type."""
        if event_name in self._listeners:
            self._listeners[event_name] = [cb for cb in self._listeners[event_name] if cb != callback]

    def publish(self, event_name: str, data: Optional[Dict[str, Any]] = None, source: str = "system") -> Event:
        """Publish a synchronous event to all registered listeners."""
        event = Event(name=event_name, data=data or {}, source=source)
        self._record_history(event)

        if event_name in self._listeners:
            for callback in self._listeners[event_name]:
                try:
                    callback(event)
                except Exception as exc:
                    logger.error(f"Error executing callback {callback.__name__} on event {event_name}: {exc}")

        return event

    async def publish_async(self, event_name: str, data: Optional[Dict[str, Any]] = None, source: str = "system") -> Event:
        """Publish an asynchronous event to registered listeners."""
        event = Event(name=event_name, data=data or {}, source=source)
        self._record_history(event)

        if event_name in self._listeners:
            tasks = []
            for callback in self._listeners[event_name]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    try:
                        callback(event)
                    except Exception as exc:
                        logger.error(f"Error executing sync callback {callback.__name__} in async publish: {exc}")

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        return event

    def _record_history(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def get_history(self, limit: int = 50) -> List[Event]:
        """Return the latest recorded events."""
        return self._history[-limit:]