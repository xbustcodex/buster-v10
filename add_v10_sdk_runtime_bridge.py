from pathlib import Path

ROOT = Path.cwd()

files = {
    "buster/runtime/sdk_runtime.py": r'''from __future__ import annotations

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
''',

    "buster/runtime/sdk_agent.py": r'''from __future__ import annotations

from typing import Any, Dict


class SDKAgent:
    agent_name = "sdk_agent"

    def __init__(self, sdk):
        self.sdk = sdk

    def publish(self, event_type: str, payload=None):
        return self.sdk.publish(event_type, payload or {}, source=self.agent_name)

    def status(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "status": "ready",
        }

    def run(self, task: Any = None):
        return self.status()
''',

    "buster/runtime/lifecycle_sdk_agent.py": r'''from __future__ import annotations

from pathlib import Path
from typing import Any

from .sdk_agent import SDKAgent


class LifecycleSDKAgent(SDKAgent):
    agent_name = "lifecycle_agent"

    def __init__(self, sdk, root: str | Path = "."):
        super().__init__(sdk)
        self.root = Path(root).resolve()
        self._manager = None

    @property
    def manager(self):
        if self._manager is None:
            from buster.lifecycle.manager import LifecycleManager
            self._manager = LifecycleManager(self.root)
        return self._manager

    def run(self, task: Any = None):
        action = "status"

        if isinstance(task, str):
            action = task
        elif isinstance(task, dict):
            action = task.get("action", "status")

        if action == "health":
            result = self.manager.run_health()
            self.publish("lifecycle.health.updated", result)
            return result

        if action == "verify":
            result = self.manager.verify()
            self.publish("lifecycle.verified", result)
            return result

        if action == "backup":
            path = self.manager.backup()
            result = {"backup_path": path}
            self.publish("lifecycle.backup.created", result)
            return result

        if action == "plan":
            result = self.manager.plan()
            self.publish("lifecycle.plan.created", result)
            return result

        result = self.manager.status()
        self.publish("lifecycle.status.checked", result)
        return result
''',

    "buster/runtime/sdk_agent_manager.py": r'''from __future__ import annotations

from typing import Any, Dict


class SDKAgentManager:
    def __init__(self, sdk):
        self.sdk = sdk
        self.agents: Dict[str, Any] = {}

    def register(self, name: str, agent: Any):
        self.agents[name] = agent
        self.sdk.register_service(f"agent.{name}", agent)
        self.sdk.publish("agent.registered", {"name": name}, source="agent_manager")
        return agent

    def get(self, name: str):
        return self.agents.get(name)

    def require(self, name: str):
        if name not in self.agents:
            raise KeyError(f"Agent not registered: {name}")
        return self.agents[name]

    def run(self, name: str, task=None):
        agent = self.require(name)
        self.sdk.publish("agent.started", {"name": name, "task": task}, source="agent_manager")
        result = agent.run(task)
        self.sdk.publish("agent.finished", {"name": name, "result": result}, source="agent_manager")
        return result

    def names(self):
        return sorted(self.agents.keys())

    def status(self):
        return {
            "count": len(self.agents),
            "agents": self.names(),
        }
''',

    "buster/runtime/sdk_bootstrap.py": r'''from __future__ import annotations

from pathlib import Path

from .sdk_agent_manager import SDKAgentManager
from .sdk_runtime import BusterSDKRuntime
from .lifecycle_sdk_agent import LifecycleSDKAgent


def build_sdk_runtime(root: str | Path = ".", observation_provider=None):
    runtime = BusterSDKRuntime(root=root, observation_provider=observation_provider)

    agents = SDKAgentManager(runtime.sdk)
    agents.register("lifecycle", LifecycleSDKAgent(runtime.sdk, root=root))

    runtime.sdk.register_service("agent_manager", agents)

    runtime.sdk.publish(
        "runtime.bootstrap.completed",
        {
            "services": runtime.sdk.registry.names(),
            "agents": agents.names(),
        },
        source="sdk_bootstrap",
    )

    return {
        "runtime": runtime,
        "sdk": runtime.sdk,
        "agents": agents,
    }
''',

    "buster/runtime/__init__.py": r'''from .engine import BusterRuntimeEngine
from .heartbeat import RuntimeHeartbeat
from .scheduler import RuntimeScheduler
from .dispatcher import RuntimeDispatcher
from .lifecycle import RuntimeLifecycle
from .watchdog import RuntimeWatchdog
from .coordinator import RuntimeCoordinator
from .idle_manager import IdleManager
from .intent_prediction import IntentPredictionEngine

from .sdk_runtime import BusterSDKRuntime
from .sdk_bootstrap import build_sdk_runtime
from .sdk_agent_manager import SDKAgentManager
from .lifecycle_sdk_agent import LifecycleSDKAgent

__all__ = [
    "BusterRuntimeEngine",
    "RuntimeHeartbeat",
    "RuntimeScheduler",
    "RuntimeDispatcher",
    "RuntimeLifecycle",
    "RuntimeWatchdog",
    "RuntimeCoordinator",
    "IdleManager",
    "IntentPredictionEngine",
    "BusterSDKRuntime",
    "build_sdk_runtime",
    "SDKAgentManager",
    "LifecycleSDKAgent",
]
''',

    "test_v10_sdk_runtime.py": r'''import json

from buster.runtime.sdk_bootstrap import build_sdk_runtime


def main():
    system = build_sdk_runtime(".")
    runtime = system["runtime"]
    sdk = system["sdk"]
    agents = system["agents"]

    print("START")
    print(json.dumps(runtime.start(), indent=4, default=str))

    print()
    print("SDK STATUS")
    print(json.dumps(sdk.status(), indent=4, default=str))

    print()
    print("SERVICES")
    print(json.dumps(sdk.registry.names(), indent=4, default=str))

    print()
    print("AGENTS")
    print(json.dumps(agents.names(), indent=4, default=str))

    print()
    print("LIFECYCLE STATUS")
    print(json.dumps(agents.run("lifecycle", "status"), indent=4, default=str))

    print()
    print("LIFECYCLE HEALTH")
    print(json.dumps(agents.run("lifecycle", "health"), indent=4, default=str))

    print()
    print("TICK")
    print(json.dumps(runtime.tick_once([{
        "type": "workspace",
        "summary": "python development in buster v10 runtime",
    }]), indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(sdk.events.recent(20), indent=4, default=str))


if __name__ == "__main__":
    main()
'''
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created/updated: {rel}")

print()
print("SDK-first v10 runtime bridge added.")
print()
print("Run:")
print("  python test_v10_sdk_runtime.py")
print("  pytest")