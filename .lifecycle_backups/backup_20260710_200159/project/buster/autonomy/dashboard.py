from __future__ import annotations

from typing import Any, Dict, Optional

from buster.autonomy.engine import AutonomyEngine


class AutonomyDashboard:
    """Small data provider for the AI OS dashboard.

    UI code can call snapshot() and render the returned dictionary without
    importing internals from the autonomy system.
    """

    def __init__(self, engine: Optional[AutonomyEngine] = None) -> None:
        self.engine = engine or AutonomyEngine()

    def snapshot(self) -> Dict[str, Any]:
        status = self.engine.status()
        last = status.get("last_decision") or {}
        return {
            "title": "Jarvis Autonomy",
            "mode": status["mode"],
            "enabled": status["enabled"],
            "active_jobs": status["active_jobs"],
            "completed_jobs": status["completed_jobs"],
            "failed_jobs": status["failed_jobs"],
            "last_action": last.get("recommended_action", "none"),
            "last_reason": last.get("reason", "No decision yet."),
            "learning_records": status.get("learning", {}).get("records", 0),
            "learned_patterns": status.get("learning", {}).get("patterns", 0),
            "updated_at": status.get("updated_at"),
        }
