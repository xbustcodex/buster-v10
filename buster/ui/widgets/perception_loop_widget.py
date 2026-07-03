from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.workspace.perception_dashboard import PerceptionDashboard


class PerceptionLoopWidgetModel:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)

    def data(self) -> Dict[str, Any]:
        snap = PerceptionDashboard(self.data_dir).snapshot()
        return {
            "title": "Real Perception Loop",
            "status": "online",
            "observations_seen": snap.get("observations_seen", 0),
            "recent_observations": snap.get("recent_observations", []),
            "last_observation": snap.get("last_observation"),
        }
