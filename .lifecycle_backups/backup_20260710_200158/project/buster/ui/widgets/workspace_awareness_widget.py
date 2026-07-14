from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.workspace.workspace_awareness_dashboard import WorkspaceAwarenessDashboard


class WorkspaceAwarenessWidgetModel:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.dashboard = WorkspaceAwarenessDashboard(data_dir=data_dir)

    def data(self) -> Dict[str, Any]:
        snap = self.dashboard.snapshot()
        return {
            "title": "Workspace Awareness",
            "status": "online" if snap["running"] else "ready",
            "event_count": snap["event_count"],
            "recent_events": snap["recent_events"],
            "messages": snap["companion_messages"],
        }
