from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.workspace.living_companion_dashboard import LivingCompanionDashboard


class LivingCompanionWidgetModel:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.dashboard = LivingCompanionDashboard(data_dir=data_dir)

    def data(self) -> Dict[str, Any]:
        snap = self.dashboard.snapshot()
        return {
            "title": "Living AI Companion",
            "status": "online" if snap["running"] else "ready",
            "mode": snap["mode"],
            "spoken": snap["spoken"],
            "skill_count": len(snap["skills"]),
            "skills": snap["skills"],
        }
