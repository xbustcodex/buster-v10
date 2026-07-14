from __future__ import annotations

from typing import Any, Dict

try:
    from buster.workspace.mind_dashboard import MindDashboard
except Exception:  # pragma: no cover
    MindDashboard = None  # type: ignore


class MindWidgetModel:
    """Pure data model for a future UI widget; no GUI dependency required."""

    def __init__(self):
        self.dashboard = MindDashboard() if MindDashboard else None

    def render_model(self) -> Dict[str, Any]:
        if self.dashboard is None:
            return {"title": "Buster Mind", "status": "unavailable"}
        return self.dashboard.snapshot()
