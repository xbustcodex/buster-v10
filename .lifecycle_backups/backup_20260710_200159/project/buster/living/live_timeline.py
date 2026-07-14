from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from .mission_events import default_message_for_event, source_for_event

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

class LiveMissionTimeline:
    """Timeline used by Mission Control to show Buster thinking live."""
    def __init__(self, path: str | Path = "data/mission_timeline_live.json", limit: int = 1000):
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

    def record(self, event_type: str, message: Optional[str] = None, *, source: Optional[str] = None, mission_id: str = "default", level: str = "info", confidence: Optional[float] = None, risk: Optional[str] = None, agent: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        event = {
            "timestamp": utc_now(),
            "mission_id": mission_id,
            "event_type": event_type,
            "source": source or agent or source_for_event(event_type),
            "agent": agent or source or source_for_event(event_type),
            "message": message or default_message_for_event(event_type),
            "level": level,
            "confidence": confidence,
            "risk": risk or "unknown",
            "details": details or {},
        }
        events = self._read()
        events.append(event)
        self._write(events)
        return event

    def recent(self, count: int = 20, mission_id: Optional[str] = None) -> List[Dict[str, Any]]:
        events = self._read()
        if mission_id:
            events = [e for e in events if e.get("mission_id") == mission_id]
        return events[-count:]

    def clear(self) -> None:
        self._write([])

    def line_for(self, event: Dict[str, Any]) -> str:
        timestamp = str(event.get("timestamp", ""))
        time_part = timestamp.split("T")[-1][:5] if "T" in timestamp else timestamp[:5]
        source = event.get("source") or event.get("agent") or "System"
        message = event.get("message") or "updated"
        confidence = event.get("confidence")
        risk = event.get("risk")
        suffix = ""
        if confidence is not None:
            try:
                suffix += f" | confidence {float(confidence) * 100:.0f}%"
            except Exception:
                suffix += f" | confidence {confidence}"
        if risk and risk != "unknown":
            suffix += f" | risk {risk}"
        return f"{time_part}  {source} {message}{suffix}"

    def lines(self, count: int = 20, mission_id: Optional[str] = None) -> List[str]:
        return [self.line_for(e) for e in self.recent(count=count, mission_id=mission_id)]
