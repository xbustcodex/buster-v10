from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LivingMood:
    STANDBY = "standby"
    THINKING = "thinking"
    WORKING = "working"
    WATCHING = "watching"
    LISTENING = "listening"
    CONFIDENT = "confident"
    CAUTIOUS = "cautious"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class LivingState:
    status: str = "online"
    mood: str = LivingMood.STANDBY
    current_mission: str = "Waiting for command"
    active_agent: str = "none"
    confidence: float = 0.0
    risk: str = "unknown"
    listening: bool = False
    watching: bool = False
    last_decision: str = ""
    last_reason: str = ""
    updated: str = field(default_factory=utc_now)
    signals: Dict[str, Any] = field(default_factory=dict)
    recent_activity: List[Dict[str, Any]] = field(default_factory=list)

    def update(self, **kwargs: Any) -> "LivingState":
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated = utc_now()
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "mood": self.mood,
            "current_mission": self.current_mission,
            "active_agent": self.active_agent,
            "confidence": self.confidence,
            "risk": self.risk,
            "listening": self.listening,
            "watching": self.watching,
            "last_decision": self.last_decision,
            "last_reason": self.last_reason,
            "updated": self.updated,
            "signals": self.signals,
            "recent_activity": self.recent_activity[-20:],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LivingState":
        return cls(
            status=data.get("status", "online"),
            mood=data.get("mood", LivingMood.STANDBY),
            current_mission=data.get("current_mission", "Waiting for command"),
            active_agent=data.get("active_agent", "none"),
            confidence=float(data.get("confidence", 0.0)),
            risk=data.get("risk", "unknown"),
            listening=bool(data.get("listening", False)),
            watching=bool(data.get("watching", False)),
            last_decision=data.get("last_decision", ""),
            last_reason=data.get("last_reason", ""),
            updated=data.get("updated", utc_now()),
            signals=data.get("signals", {}),
            recent_activity=data.get("recent_activity", []),
        )
