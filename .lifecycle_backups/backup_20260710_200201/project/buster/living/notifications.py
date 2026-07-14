from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class DecisionNotification:
    title: str
    message: str
    reason: str = ""
    confidence: float = 0.0
    risk: str = "unknown"
    action: str = ""
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "title": self.title,
            "message": self.message,
            "reason": self.reason,
            "confidence": self.confidence,
            "risk": self.risk,
            "action": self.action,
        }


class NotificationCenter:
    def __init__(self, path: str | Path = "data/decision_notifications.json", limit: int = 200):
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

    def notify_decision(self, title: str, message: str, reason: str = "", confidence: float = 0.0, risk: str = "unknown", action: str = "") -> Dict[str, Any]:
        notice = DecisionNotification(
            title=title,
            message=message,
            reason=reason,
            confidence=confidence,
            risk=risk,
            action=action,
        ).to_dict()
        notices = self._read()
        notices.append(notice)
        self.path.write_text(json.dumps(notices[-self.limit:], indent=2), encoding="utf-8")
        return notice

    def recent(self, count: int = 10) -> List[Dict[str, Any]]:
        return self._read()[-count:]
