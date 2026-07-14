from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AIOSStatus:
    online: bool = True
    mode: str = "standby"
    current_mission: str = "Waiting for command"
    confidence: float = 0.0
    risk: str = "unknown"
    strategy: List[str] = field(default_factory=list)
    active_agents: List[str] = field(default_factory=list)
    plugins_loaded: int = 0
    learning_items: int = 0
    experience_items: int = 0
    events_recorded: int = 0
    updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "online": self.online,
            "mode": self.mode,
            "current_mission": self.current_mission,
            "confidence": self.confidence,
            "risk": self.risk,
            "strategy": list(self.strategy),
            "active_agents": list(self.active_agents),
            "plugins_loaded": self.plugins_loaded,
            "learning_items": self.learning_items,
            "experience_items": self.experience_items,
            "events_recorded": self.events_recorded,
            "updated": self.updated,
        }
