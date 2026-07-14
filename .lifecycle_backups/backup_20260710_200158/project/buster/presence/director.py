from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List
from .modes import PresenceMode, PresencePriority, PRIORITY_SCORE

DEFAULT_SETTINGS = {
    "enabled": True, "mode": PresenceMode.COMPANION, "quiet_mode": False,
    "cooldown_seconds": 20, "max_items_per_hour": 24, "min_priority": PresencePriority.NORMAL,
    "allow_greetings": True, "allow_idle_checkins": True,
    "allow_camera_learning_comments": True, "allow_engineering_suggestions": True,
}

class ConversationDirector:
    """Single gatekeeper that decides if Buster should talk first."""
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir); self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.data_dir / "presence_settings.json"
        self.queue_path = self.data_dir / "presence_speech_queue.json"
        self.state_path = self.data_dir / "presence_state.json"
        self.settings = self._load_json(self.settings_path, DEFAULT_SETTINGS)
        self._ensure_files()
    def _now(self) -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            path.write_text(json.dumps(default, indent=2), encoding="utf-8")
            return default.copy() if isinstance(default, dict) else default
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return default.copy() if isinstance(default, dict) else default
    def _save_json(self, path: Path, data: Any) -> None: path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    def _ensure_files(self) -> None:
        self._load_json(self.queue_path, [])
        self._load_json(self.state_path, {"mode": self.settings.get("mode", PresenceMode.COMPANION), "last_spoken": None, "last_emotion": "relaxed", "updated": self._now()})
    def set_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in [PresenceMode.SILENT, PresenceMode.ASSISTANT, PresenceMode.COMPANION, PresenceMode.ENGINEER]: raise ValueError(f"Unknown presence mode: {mode}")
        self.settings["mode"] = mode; self._save_json(self.settings_path, self.settings)
        state = self._load_json(self.state_path, {}); state.update({"mode": mode, "updated": self._now()}); self._save_json(self.state_path, state); return state
    def should_speak(self, priority: str = PresencePriority.NORMAL, category: str = "general") -> bool:
        if not self.settings.get("enabled", True): return False
        if self.settings.get("quiet_mode", False): return priority == PresencePriority.URGENT
        mode = self.settings.get("mode", PresenceMode.COMPANION)
        if mode == PresenceMode.SILENT: return priority == PresencePriority.URGENT
        if mode == PresenceMode.ASSISTANT and priority == PresencePriority.LOW: return False
        if mode == PresenceMode.ENGINEER and category not in ["engineering", "mission", "error", "learning", "system"]: return priority in [PresencePriority.IMPORTANT, PresencePriority.URGENT]
        min_priority = self.settings.get("min_priority", PresencePriority.NORMAL)
        return PRIORITY_SCORE.get(priority, 2) >= PRIORITY_SCORE.get(min_priority, 2)
    def request_speech(self, message: str, priority: str = PresencePriority.NORMAL, category: str = "general", reason: str = "") -> Dict[str, Any]:
        item = {"timestamp": self._now(), "message": message, "priority": priority, "category": category, "reason": reason, "approved": self.should_speak(priority, category)}
        queue: List[Dict[str, Any]] = self._load_json(self.queue_path, []); queue.append(item); self._save_json(self.queue_path, queue[-250:]); return item
    def greeting(self, name: str = "Adam") -> Dict[str, Any]: return self.request_speech(f"Good morning {name}. I'm online and ready.", PresencePriority.NORMAL, "presence", "daily greeting")
    def engineering_update(self, message: str, reason: str = "engineering update") -> Dict[str, Any]: return self.request_speech(message, PresencePriority.IMPORTANT, "engineering", reason)
