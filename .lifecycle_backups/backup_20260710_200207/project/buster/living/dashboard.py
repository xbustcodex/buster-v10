from __future__ import annotations

from typing import Any, Dict, List

from .engine import LivingOSEngine


class LivingDashboard:
    """
    Dashboard data provider for Jarvis-style live UI.

    UI code can call snapshot() and render:
    face, current mission, confidence/risk, timeline,
    notifications, voice state, and vision state.
    """

    def __init__(self):
        self.engine = LivingOSEngine()

    def snapshot(self) -> Dict[str, Any]:
        return self.engine.status()

    def timeline_lines(self, count: int = 10) -> List[str]:
        events = self.engine.timeline.list_recent(count)
        lines = []
        for event in events:
            timestamp = event.get("timestamp", "")
            time_part = timestamp.split("T")[-1][:5] if "T" in timestamp else timestamp[:5]
            source = event.get("source", "System")
            message = event.get("message", "")
            lines.append(f"{time_part}  {source} {message}")
        return lines
