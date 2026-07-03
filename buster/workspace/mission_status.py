from buster.utils.datetime_utils import utc_now, utc_timestamp
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class MissionStatus:
    name: str = "Buster AI OS"
    mode: str = "READY"
    confidence: float = 0.0
    risk: str = "unknown"
    active_agents: int = 0
    running_jobs: int = 0
    plugins_loaded: int = 0
    learning_entries: int = 0
    experience_entries: int = 0
    skills_tracked: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data.get("last_updated"):
            data["last_updated"] = utc_now().replace(tzinfo=None).isoformat(timespec="seconds")
        return data


class MissionTimeline:
    def __init__(self, max_items: int = 100):
        self.max_items = max_items
        self.items: List[Dict[str, Any]] = []

    def add(self, event_type: str, message: str, source: str = "mission_control") -> Dict[str, Any]:
        item = {
            "time": utc_now().replace(tzinfo=None).isoformat(timespec="seconds"),
            "event_type": event_type,
            "source": source,
            "message": message,
        }
        self.items.append(item)
        self.items = self.items[-self.max_items:]
        return item

    def latest(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(reversed(self.items[-limit:]))
