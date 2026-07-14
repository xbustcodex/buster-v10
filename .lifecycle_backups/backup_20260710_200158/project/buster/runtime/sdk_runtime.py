from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.sdk import BusterSDK
from buster.runtime.engine import BusterRuntimeEngine


class BusterSDKRuntime:
    """
    v10 SDK-first runtime.

    This makes the existing BusterSDK the central API surface:
    - SDK events become the main event bus
    - SDK registry becomes the service registry
    - SDK lifecycle becomes the module lifecycle manager
    """

    def __init__(self, root: str | Path = ".", observation_provider=None):
        self.root = Path(root).resolve()
        self.sdk = BusterSDK(data_dir=self.root / "data")
        self.engine = BusterRuntimeEngine(observation_provider=observation_provider)

        self.register_core_services()
        self.register_core_modules()
        self.wire_runtime_events()

    @property
    def events(self):
        return self.sdk.events

    @property
    def registry(self):
        return self.sdk.registry

    @property
    def lifecycle(self):
        return self.sdk.lifecycle

    def register_core_services(self):
        self.sdk.register_service("sdk", self.sdk)
        self.sdk.register_service("runtime_engine", self.engine)
        self.sdk.register_service("dispatcher_legacy", self.engine.dispatcher)
        self.sdk.register_service("scheduler", self.engine.scheduler)
        self.sdk.register_service("heartbeat", self.engine.heartbeat)
        self.sdk.register_service("runtime_lifecycle", self.engine.lifecycle)
        self.sdk.register_service("watchdog", self.engine.watchdog)
        self.sdk.register_service("coordinator", self.engine.coordinator)
        self.sdk.register_service("idle_manager", self.engine.idle)
        self.sdk.register_service("intent_prediction", self.engine.predictor)

    def register_core_modules(self):
        self.sdk.register_module("runtime_engine", self.engine)

    def wire_runtime_events(self):
        def mirror_runtime_tick(event):
            self.sdk.publish(
                "runtime.tick.mirrored",
                {
                    "legacy_event": event.get("type"),
                    "payload": event.get("payload", {}),
                    "created_at": event.get("created_at"),
                },
                source="runtime_bridge",
            )

        self.engine.dispatcher.subscribe("runtime.tick", mirror_runtime_tick)

    def start(self) -> Dict[str, Any]:
        engine_result = self.engine.start()
        self.sdk.publish("runtime.started", engine_result, source="sdk_runtime")
        return {
            "runtime": "started",
            "engine": engine_result,
            "sdk": self.sdk.status(),
        }

    def stop(self) -> Dict[str, Any]:
        engine_result = self.engine.stop()
        self.sdk.publish("runtime.stopped", engine_result, source="sdk_runtime")
        return {
            "runtime": "stopped",
            "engine": engine_result,
            "sdk": self.sdk.status(),
        }

    def tick_once(self, observations=None) -> Dict[str, Any]:
        result = self.engine.tick_once(observations)
        self.sdk.publish("runtime.tick", result, source="sdk_runtime")
        return result

    def status(self) -> Dict[str, Any]:
        return {
            "root": str(self.root),
            "sdk": self.sdk.status(),
            "engine": self.engine.status(),
            "events": self.sdk.events.recent(20),
        }

    def service(self, name: str, default=None):
        return self.sdk.service(name, default)

    def require_service(self, name: str):
        return self.sdk.require_service(name)

    def publish(self, event_type: str, payload=None, source="sdk_runtime"):
        return self.sdk.publish(event_type, payload or {}, source=source)

    def subscribe(self, event_type: str, handler):
        return self.sdk.subscribe(event_type, handler)
