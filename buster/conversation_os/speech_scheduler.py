from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .modes import PRIORITY_SCORE
from .settings import ProactiveSpeechSettings
from .speech_queue import SpeechQueue


def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


class ProactiveSpeechScheduler:
    def __init__(self, queue: SpeechQueue | None = None, settings: ProactiveSpeechSettings | None = None) -> None:
        self.queue = queue or SpeechQueue()
        self.settings = settings or ProactiveSpeechSettings()

    def should_speak(self, item: Dict[str, Any], history: List[Dict[str, Any]] | None = None) -> tuple[bool, str]:
        cfg = self.settings.load()
        if not cfg.get("enabled", True):
            return False, "proactive speech disabled"
        if cfg.get("quiet_mode", False) and item.get("priority") != "urgent":
            return False, "quiet mode active"
        min_priority = cfg.get("min_priority", "normal")
        if PRIORITY_SCORE.get(item.get("priority", "normal"), 2) < PRIORITY_SCORE.get(min_priority, 2):
            return False, "below priority threshold"

        history = history or []
        now = datetime.now(timezone.utc)
        spoken_times = [parse_time(h.get("spoken_at")) for h in history if h.get("spoken_at")]
        spoken_times = [t for t in spoken_times if t is not None]

        if spoken_times:
            last = max(spoken_times)
            if (now - last).total_seconds() < int(cfg.get("cooldown_seconds", 20)) and item.get("priority") != "urgent":
                return False, "cooldown active"

        hour_count = sum(1 for t in spoken_times if now - t < timedelta(hours=1))
        if hour_count >= int(cfg.get("max_items_per_hour", 18)) and item.get("priority") != "urgent":
            return False, "hourly speech limit reached"

        return True, "allowed"

    def next_item(self) -> Dict[str, Any] | None:
        pending = self.queue.pending()
        if not pending:
            return None
        all_items = self.queue._load()
        pending.sort(key=lambda i: PRIORITY_SCORE.get(i.get("priority", "normal"), 2), reverse=True)
        for item in pending:
            ok, reason = self.should_speak(item, all_items)
            if ok:
                item["scheduler_reason"] = reason
                return item
        return None

    def pop_next_for_speech(self) -> Dict[str, Any] | None:
        item = self.next_item()
        if not item:
            return None
        self.queue.mark_spoken(item["id"])
        return item