from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.workspace.autonomous_mission_dashboard import AutonomousMissionDashboard


class AutonomousMissionWidgetModel:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.dashboard = AutonomousMissionDashboard(data_dir=data_dir)

    def data(self) -> Dict[str, Any]:
        snap = self.dashboard.snapshot()
        return {
            "title": "Autonomous Mission Runtime",
            "status": "online" if snap["running"] else "ready",
            "queued": snap["queued"],
            "completed": snap["completed"],
            "capability_count": len(snap["capabilities"]),
            "messages": snap["messages"],
        }
