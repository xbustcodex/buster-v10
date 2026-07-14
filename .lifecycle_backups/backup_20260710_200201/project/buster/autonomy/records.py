from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from buster.utils.datetime_utils import utc_timestamp
from typing import Any, Dict, List
import uuid


def utc_now() -> str:
    return utc_timestamp()


@dataclass
class AutonomyDecision:
    """A single planner decision made by the Jarvis autonomy layer."""

    request: str
    project_type: str = "general"
    recommended_action: str = "inspect"
    confidence: float = 0.5
    reason: str = "No reason recorded."
    strategy: str = "general"
    plugins: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyDecision":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class AutonomyJob:
    """One autonomous task/session record."""

    title: str
    request: str
    project: str = "default"
    project_type: str = "general"
    status: str = "queued"  # queued, running, completed, failed, paused
    assigned_agents: List[str] = field(default_factory=list)
    decision: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def update_status(self, status: str, result: Dict[str, Any] | None = None) -> None:
        self.status = status
        self.updated_at = utc_now()
        if result is not None:
            self.result = result

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyJob":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in allowed})
