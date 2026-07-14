
from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AgentActivityFeed:
    def __init__(self, path: str | Path = "data/agent_activity_feed.json", limit: int = 250):
        self.path = Path(path)
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write(self, events: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(events[-self.limit:], indent=2), encoding="utf-8")

    def record(self, agent: str, status: str, message: str, confidence: float = 0.0, risk: str = "unknown", mission_id: str = "default") -> Dict[str, Any]:
        item = {
            "time": utc_now(),
            "mission_id": mission_id,
            "agent": agent,
            "status": status,
            "message": message,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "risk": risk,
        }
        events = self._read()
        events.append(item)
        self._write(events)
        return item

    def latest(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._read()[-limit:]
