from __future__ import annotations

from typing import Any, Dict

from buster.living.dashboard import LivingDashboard


class LivingOSWidgetModel:
    """
    UI-safe model for the living dashboard.

    This avoids requiring a specific GUI framework. Existing UI code can
    read this model and render it into the current dashboard.
    """

    def __init__(self):
        self.dashboard = LivingDashboard()

    def get_view_model(self) -> Dict[str, Any]:
        snapshot = self.dashboard.snapshot()
        return {
            "title": "Buster Living OS",
            "status": snapshot.get("status", "online"),
            "mood": snapshot.get("mood", "standby"),
            "face": snapshot.get("face", {}),
            "mission": snapshot.get("current_mission", "Waiting for command"),
            "agent": snapshot.get("active_agent", "none"),
            "confidence": snapshot.get("confidence", 0.0),
            "risk": snapshot.get("risk", "unknown"),
            "listening": snapshot.get("listening", False),
            "watching": snapshot.get("watching", False),
            "timeline": self.dashboard.timeline_lines(10),
            "notifications": snapshot.get("notifications", []),
        }
