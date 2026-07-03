from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List
import uuid


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class MissionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MissionStep:
    title: str
    capability: str
    assigned_agent: str | None = None
    status: StepStatus = StepStatus.PENDING
    result: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: str = field(default_factory=now_utc)
    updated: str = field(default_factory=now_utc)

    def start(self, agent: str | None = None) -> None:
        self.status = StepStatus.RUNNING
        if agent:
            self.assigned_agent = agent
        self.updated = now_utc()

    def complete(self, result: Dict[str, Any] | None = None) -> None:
        self.status = StepStatus.COMPLETED
        self.result = result or {}
        self.updated = now_utc()

    def fail(self, error: str) -> None:
        self.status = StepStatus.FAILED
        self.result = {"error": error}
        self.updated = now_utc()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "capability": self.capability,
            "assigned_agent": self.assigned_agent,
            "status": self.status.value,
            "result": self.result,
            "created": self.created,
            "updated": self.updated,
        }


@dataclass
class Mission:
    title: str
    intent: str = "general"
    steps: List[MissionStep] = field(default_factory=list)
    status: MissionStatus = MissionStatus.CREATED
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: str = field(default_factory=now_utc)
    updated: str = field(default_factory=now_utc)

    def add_step(self, title: str, capability: str, assigned_agent: str | None = None) -> MissionStep:
        step = MissionStep(title=title, capability=capability, assigned_agent=assigned_agent)
        self.steps.append(step)
        self.updated = now_utc()
        return step

    def start(self) -> None:
        self.status = MissionStatus.RUNNING
        self.updated = now_utc()

    def complete(self) -> None:
        self.status = MissionStatus.COMPLETED
        self.updated = now_utc()

    def fail(self) -> None:
        self.status = MissionStatus.FAILED
        self.updated = now_utc()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "intent": self.intent,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "created": self.created,
            "updated": self.updated,
        }
