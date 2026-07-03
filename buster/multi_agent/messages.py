from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List
import uuid

def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

@dataclass
class AgentMessage:
    agent: str
    message: str
    kind: str = "status"
    data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=now_utc)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "timestamp": self.timestamp, "agent": self.agent, "kind": self.kind, "message": self.message, "data": self.data}

@dataclass
class CollaborationDecision:
    mission: str
    chosen_agent: str
    reason: str
    confidence: float
    next_agents: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=now_utc)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "timestamp": self.timestamp, "mission": self.mission, "chosen_agent": self.chosen_agent, "reason": self.reason, "confidence": self.confidence, "next_agents": self.next_agents}
