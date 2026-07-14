from __future__ import annotations

from typing import Any, Dict

from buster.mind import MindEngine


class MindDashboard:
    """Dashboard model for Mission Control's cognitive view."""

    def __init__(self, mind: MindEngine | None = None):
        self.mind = mind or MindEngine()

    def snapshot(self) -> Dict[str, Any]:
        state = self.mind.think()
        return {
            "title": "Buster Mind",
            "current_focus": state.get("attention", {}).get("current_focus"),
            "working_memory": state.get("working_memory"),
            "active_goals": state.get("active_goals", []),
            "curiosity": state.get("curiosity_suggestions", []),
            "status": "thinking" if state.get("attention", {}).get("current_focus") else "relaxed",
        }
