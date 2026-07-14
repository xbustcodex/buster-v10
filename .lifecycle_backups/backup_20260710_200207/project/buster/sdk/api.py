from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict

from .config import SafeConfig
from .events import UnifiedEventAPI, EventPriority, Event
from .lifecycle import ModuleLifecycle
from .registry import ServiceRegistry


class BusterSDK:
    """Stable internal API surface for Buster v6."""

    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.events = UnifiedEventAPI()
        self.registry = ServiceRegistry()
        self.lifecycle = ModuleLifecycle()
        self.config = SafeConfig(self.data_dir / "v6_safe_config.json")

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any] | None = None,
        source: str = "sdk",
        priority: EventPriority | str = EventPriority.NORMAL,
    ) -> Event:
        return self.events.publish(event_type, payload, source, priority)

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self.events.subscribe(event_type, handler)

    def register_service(self, name: str, service: Any) -> Any:
        return self.registry.register(name, service)

    def service(self, name: str, default: Any = None) -> Any:
        return self.registry.get(name, default)

    def require_service(self, name: str) -> Any:
        return self.registry.require(name)

    def register_module(self, name: str, module: Any) -> None:
        self.lifecycle.register(name, module)
        self.registry.register(name, module)

    def start(self) -> Dict[str, Any]:
        result = self.lifecycle.start_all()
        self.publish("sdk.started", {"modules": self.lifecycle.status()}, source="sdk")
        return result

    def stop(self) -> Dict[str, Any]:
        result = self.lifecycle.stop_all()
        self.publish("sdk.stopped", {"modules": self.lifecycle.status()}, source="sdk")
        return result

    def observe(self, summary: str, source: str = "sdk", **payload: Any) -> Event:
        data = {"summary": summary}
        data.update(payload)
        return self.publish("perception.observation", data, source=source)

    def speak(self, message: str, reason: str = "sdk") -> Event:
        return self.publish("companion.speech", {"message": message, "reason": reason}, source="sdk")

    def learn(self, pattern: str, data: Dict[str, Any] | None = None) -> Event:
        return self.publish("learning.pattern", {"pattern": pattern, "data": data or {}}, source="sdk")

    def create_goal(self, title: str, **payload: Any) -> Event:
        data = {"title": title}
        data.update(payload)
        return self.publish("mind.goal.created", data, source="sdk")

    def status(self) -> Dict[str, Any]:
        return {
            "services": self.registry.status(),
            "modules": self.lifecycle.status(),
            "events": len(self.events.history),
            "config": self.config.status(),
        }
