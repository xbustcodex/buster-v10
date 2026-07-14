from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Protocol


class LifecycleState(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class LifecycleModule(Protocol):
    def start(self) -> Dict[str, Any]: ...
    def stop(self) -> Dict[str, Any]: ...
    def status(self) -> Dict[str, Any]: ...


class ModuleLifecycle:
    def __init__(self) -> None:
        self.modules: Dict[str, Any] = {}
        self.states: Dict[str, LifecycleState] = {}

    def register(self, name: str, module: Any) -> None:
        self.modules[name] = module
        self.states[name] = LifecycleState.CREATED

    def start(self, name: str) -> Dict[str, Any]:
        module = self.modules[name]
        self.states[name] = LifecycleState.STARTING
        try:
            result = module.start() if hasattr(module, "start") else {"running": True}
            self.states[name] = LifecycleState.RUNNING
            return {"module": name, "state": self.states[name].value, "result": result}
        except Exception as exc:
            self.states[name] = LifecycleState.ERROR
            return {"module": name, "state": "error", "error": str(exc)}

    def stop(self, name: str) -> Dict[str, Any]:
        module = self.modules[name]
        self.states[name] = LifecycleState.STOPPING
        try:
            result = module.stop() if hasattr(module, "stop") else {"running": False}
            self.states[name] = LifecycleState.STOPPED
            return {"module": name, "state": self.states[name].value, "result": result}
        except Exception as exc:
            self.states[name] = LifecycleState.ERROR
            return {"module": name, "state": "error", "error": str(exc)}

    def start_all(self) -> Dict[str, Any]:
        return {name: self.start(name) for name in list(self.modules)}

    def stop_all(self) -> Dict[str, Any]:
        return {name: self.stop(name) for name in reversed(list(self.modules))}

    def status(self) -> Dict[str, Any]:
        return {name: state.value for name, state in self.states.items()}
