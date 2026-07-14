from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List
import uuid


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class IntentHypothesis:
    intent: str
    summary: str
    confidence: float
    recommended_actions: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    risk: str = "low"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=now_utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "intent": self.intent,
            "summary": self.summary,
            "confidence": self.confidence,
            "recommended_actions": self.recommended_actions,
            "evidence": self.evidence,
            "risk": self.risk,
        }
