from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict
import uuid


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class SkillLevel:
    score: float = 0.5
    successes: int = 0
    failures: int = 0

    def update(self, success: bool, weight: float = 0.02) -> None:
        if success:
            self.successes += 1
            self.score = min(1.0, self.score + weight)
        else:
            self.failures += 1
            self.score = max(0.0, self.score - weight)

    def percent(self) -> float:
        return round(self.score * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "percent": self.percent(),
            "successes": self.successes,
            "failures": self.failures,
        }


@dataclass
class Skill:
    name: str
    domain: str
    description: str = ""
    level: SkillLevel = field(default_factory=SkillLevel)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    updated: str = field(default_factory=now_utc)

    def record_result(self, success: bool, weight: float = 0.02) -> None:
        self.level.update(success, weight)
        self.updated = now_utc()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "level": self.level.to_dict(),
            "updated": self.updated,
        }
