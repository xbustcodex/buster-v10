from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any

@dataclass
class VisualObservation:
    label: str
    source: str = "camera"
    confidence: float = 0.0
    context: str = ""
    details: Dict[str, Any] | None = None
    timestamp: str = ""
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data.get("timestamp"): data["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if data.get("details") is None: data["details"] = {}
        return data
