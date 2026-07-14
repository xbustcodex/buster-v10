from __future__ import annotations
from typing import Any, Dict
from buster.workspace.live_mission_timeline import LiveMissionTimelineView

class LiveMissionTimelineWidgetModel:
    """UI-safe widget model for the Jarvis-style live timeline."""
    def __init__(self):
        self.view = LiveMissionTimelineView()
    def get_view_model(self) -> Dict[str, Any]:
        model = self.view.get_view_model(20)
        model["empty_message"] = "No mission activity yet. Start a mission to watch Buster think."
        return model
