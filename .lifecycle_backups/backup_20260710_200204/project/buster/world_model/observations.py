from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

@dataclass
class Observation:
    source: str
    summary: str
    context: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    confidence: float = 0.75
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return Observation(**data)
