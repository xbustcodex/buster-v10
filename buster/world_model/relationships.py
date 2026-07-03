from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import uuid

@dataclass
class Relationship:
    source_id: str
    target_id: str
    relation: str
    confidence: float = 0.75
    relationship_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return Relationship(**data)
