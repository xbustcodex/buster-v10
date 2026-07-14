
from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AgentConversation:
    def __init__(self, path: str | Path = "data/agent_conversation.json", limit: int = 250):
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

    def _write(self, messages: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(messages[-self.limit:], indent=2), encoding="utf-8")

    def say(self, speaker: str, text: str, reason: str = "", confidence: float = 0.0, mission_id: str = "default", visible_to_user: bool = True) -> Dict[str, Any]:
        item = {
            "time": utc_now(),
            "mission_id": mission_id,
            "speaker": speaker,
            "text": text,
            "reason": reason,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "visible_to_user": bool(visible_to_user),
        }
        messages = self._read()
        messages.append(item)
        self._write(messages)
        return item

    def latest(self, limit: int = 20, user_visible_only: bool = False) -> List[Dict[str, Any]]:
        messages = self._read()
        if user_visible_only:
            messages = [m for m in messages if m.get("visible_to_user", True)]
        return messages[-limit:]
