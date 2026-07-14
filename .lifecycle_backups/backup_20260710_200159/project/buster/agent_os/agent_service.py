from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentService:
    name: str
    role: str
    state: AgentState = AgentState.IDLE
    last_message: str = ""
    task_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self) -> Dict[str, Any]:
        self.state = AgentState.IDLE
        self.last_message = f"{self.name} online"
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.state = AgentState.IDLE
        self.last_message = f"{self.name} stopped"
        return self.status()

    def assign(self, task: str, **metadata: Any) -> Dict[str, Any]:
        self.state = AgentState.WORKING
        self.task_count += 1
        self.metadata.update(metadata)
        self.last_message = task
        return self.status()

    def complete(self, message: str = "Task complete") -> Dict[str, Any]:
        self.state = AgentState.DONE
        self.last_message = message
        return self.status()

    def fail(self, message: str) -> Dict[str, Any]:
        self.state = AgentState.ERROR
        self.last_message = message
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "state": self.state.value,
            "last_message": self.last_message,
            "task_count": self.task_count,
            "metadata": self.metadata,
            "updated": now_utc(),
        }
