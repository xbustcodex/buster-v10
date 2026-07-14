from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class ExperienceRecord:
    """One reusable lesson from a Buster job."""

    task: str
    project: str = "default"
    outcome: str = "unknown"  # success, failure, partial
    strategy: str = "general"
    what_worked: List[str] = field(default_factory=list)
    what_failed: List[str] = field(default_factory=list)
    fixes: List[str] = field(default_factory=list)
    reusable_patterns: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceRecord":
        known = {field.name for field in cls.__dataclass_fields__.values()}
        cleaned = {key: value for key, value in data.items() if key in known}
        return cls(**cleaned)
