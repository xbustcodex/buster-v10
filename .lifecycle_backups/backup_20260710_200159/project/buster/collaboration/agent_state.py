
from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AgentStatus:
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    LEARNING = "learning"
    BUILDING = "building"
    TESTING = "testing"
    FIXING = "fixing"
    REVIEWING = "reviewing"
    VERIFYING = "verifying"
    MONITORING = "monitoring"
    WAITING = "waiting"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class AgentState:
    name: str
    role: str
    status: str = AgentStatus.IDLE
    message: str = ""
    confidence: float = 0.0
    risk: str = "unknown"
    updated: str = ""

    def __post_init__(self) -> None:
        if not self.updated:
            self.updated = utc_now()

    def update(self, status: str, message: str = "", confidence: float | None = None, risk: str | None = None) -> "AgentState":
        self.status = status
        self.message = message
        if confidence is not None:
            self.confidence = max(0.0, min(1.0, float(confidence)))
        if risk is not None:
            self.risk = risk
        self.updated = utc_now()
        return self

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
