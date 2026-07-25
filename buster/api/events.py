from __future__ import annotations

from typing import Any, Callable, Dict, List


class EventBroadcaster:
    """Manages event subscriptions and broadcasts state changes to Mission Control clients."""

    def __init__(self) -> None:
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback listener for realtime events."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a callback listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def publish(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcasts an event payload to all active listeners."""
        payload = {
            "event_type": event_type,
            "data": data,
        }
        for listener in self._listeners:
            try:
                listener(payload)
            except Exception:
                pass  # Keep channel resilient if a listener fails
        return payload