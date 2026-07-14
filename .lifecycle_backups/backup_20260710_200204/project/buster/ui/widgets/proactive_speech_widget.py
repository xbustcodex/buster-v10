from __future__ import annotations

from typing import Dict, Any

try:
    from buster.workspace.proactive_speech_dashboard import ProactiveSpeechDashboard
except Exception:  # pragma: no cover
    ProactiveSpeechDashboard = None  # type: ignore


class ProactiveSpeechWidgetModel:
    def __init__(self) -> None:
        self.dashboard = ProactiveSpeechDashboard() if ProactiveSpeechDashboard is not None else None

    def render_model(self) -> Dict[str, Any]:
        if self.dashboard is None:
            return {"title": "Proactive Speech", "available": False}
        snap = self.dashboard.snapshot()
        return {
            "title": "Proactive Speech",
            "subtitle": "Buster can speak first when important things happen.",
            **snap,
        }
