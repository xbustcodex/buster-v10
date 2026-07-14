from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any

from .modes import TalkMode


DEFAULT_SETTINGS = {
    "enabled": True,
    "mode": TalkMode.BALANCED,
    "quiet_mode": False,
    "speak_agent_updates": True,
    "speak_mission_events": True,
    "speak_decisions": True,
    "speak_errors": True,
    "speak_success": True,
    "min_priority": "normal",
    "cooldown_seconds": 20,
    "max_items_per_hour": 18,
    "allow_idle_checkins": True,
    "idle_checkin_minutes": 30,
}


@dataclass
class ProactiveSpeechSettings:
    path: str = "data/proactive_speech_settings.json"

    def load(self) -> Dict[str, Any]:
        target = Path(self.path)
        if not target.exists():
            return dict(DEFAULT_SETTINGS)
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data if isinstance(data, dict) else {})
        return merged

    def save(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        data = self.load()
        data.update(updates)
        target = Path(self.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def set_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in {TalkMode.SILENT, TalkMode.QUIET, TalkMode.BALANCED, TalkMode.TALKATIVE, TalkMode.JARVIS}:
            raise ValueError(f"Unknown talk mode: {mode}")
        updates = {"mode": mode, "enabled": mode != TalkMode.SILENT}
        if mode == TalkMode.QUIET:
            updates.update({"cooldown_seconds": 60, "max_items_per_hour": 6, "min_priority": "important"})
        elif mode == TalkMode.BALANCED:
            updates.update({"cooldown_seconds": 20, "max_items_per_hour": 18, "min_priority": "normal"})
        elif mode == TalkMode.TALKATIVE:
            updates.update({"cooldown_seconds": 8, "max_items_per_hour": 40, "min_priority": "low"})
        elif mode == TalkMode.JARVIS:
            updates.update({"cooldown_seconds": 5, "max_items_per_hour": 60, "min_priority": "low", "allow_idle_checkins": True})
        return self.save(updates)
