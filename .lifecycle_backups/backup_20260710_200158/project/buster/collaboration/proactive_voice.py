
from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProactiveVoicePresence:
    def __init__(self, path: str | Path = "data/proactive_voice_queue.json", settings_path: str | Path = "data/proactive_voice_settings.json"):
        self.path = Path(path)
        self.settings_path = Path(settings_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")
        if not self.settings_path.exists():
            self.settings_path.write_text(json.dumps({
                "enabled": True,
                "quiet_mode": False,
                "talk_when_idle": True,
                "talk_on_mission_events": True,
                "minimum_priority": "normal",
                "updated": utc_now(),
            }, indent=2), encoding="utf-8")

    def settings(self) -> Dict[str, Any]:
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            return {"enabled": True, "quiet_mode": False}

    def set_enabled(self, enabled: bool) -> Dict[str, Any]:
        data = self.settings()
        data["enabled"] = bool(enabled)
        data["updated"] = utc_now()
        self.settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def _read_queue(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_queue(self, queue: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(queue[-200:], indent=2), encoding="utf-8")

    def speak(self, text: str, reason: str = "", priority: str = "normal", confidence: float = 0.0, interrupt: bool = False) -> Dict[str, Any]:
        settings = self.settings()
        item = {
            "time": utc_now(),
            "text": text,
            "reason": reason,
            "priority": priority,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "interrupt": bool(interrupt),
            "enabled": bool(settings.get("enabled", True)) and not bool(settings.get("quiet_mode", False)),
            "spoken": False,
        }
        queue = self._read_queue()
        queue.append(item)
        self._write_queue(queue)
        return item

    def pending(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [m for m in self._read_queue() if not m.get("spoken", False)][-limit:]

    def mark_spoken(self, index: int) -> None:
        queue = self._read_queue()
        if 0 <= index < len(queue):
            queue[index]["spoken"] = True
            queue[index]["spoken_at"] = utc_now()
            self._write_queue(queue)
