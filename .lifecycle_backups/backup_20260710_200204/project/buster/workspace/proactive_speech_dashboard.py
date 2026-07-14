from __future__ import annotations

from typing import Dict, Any

try:
    from buster.conversation_os import ConversationOS
except Exception:  # pragma: no cover
    ConversationOS = None  # type: ignore


class ProactiveSpeechDashboard:
    def __init__(self) -> None:
        self.os = ConversationOS() if ConversationOS is not None else None

    def snapshot(self) -> Dict[str, Any]:
        if self.os is None:
            return {"available": False, "pending_speech": 0, "mode": "unknown"}
        status = self.os.status()
        settings = status.get("settings", {})
        return {
            "available": True,
            "enabled": settings.get("enabled"),
            "mode": settings.get("mode"),
            "quiet_mode": settings.get("quiet_mode"),
            "pending_speech": status.get("pending_speech", 0),
            "cooldown_seconds": settings.get("cooldown_seconds"),
            "max_items_per_hour": settings.get("max_items_per_hour"),
        }
