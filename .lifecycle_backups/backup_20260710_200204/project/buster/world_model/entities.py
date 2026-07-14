from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

@dataclass
class WorldEntity:
    kind: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    confidence: float = 0.75
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def update(self, **attrs):
        self.attributes.update(attrs)
        self.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return self

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return WorldEntity(**data)
