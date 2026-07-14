from typing import Any, Dict, List

from buster.workspace.mission_control_dashboard import MissionControlDashboard


class MissionPlanner:
    """Planner helper that checks Mission Control before choosing actions."""

    def __init__(self, data_dir: str = "data"):
        self.dashboard = MissionControlDashboard(data_dir=data_dir)

    def recommend(self, request: str = "") -> Dict[str, Any]:
        snap = self.dashboard.snapshot()
        health = snap.get("health", "WATCH")
        status = snap.get("status", {})
        confidence = float(status.get("confidence") or 0.0)
        risk = str(status.get("risk") or "unknown")

        actions: List[str] = []
        if health == "GOOD":
            actions.append("Proceed with autonomous execution")
        elif health == "WATCH":
            actions.append("Proceed with verification checkpoints")
        else:
            actions.append("Ask user before executing risky changes")

        if status.get("plugins_loaded", 0) == 0:
            actions.append("Refresh plugin registry")
        if status.get("learning_entries", 0) == 0:
            actions.append("Record first learning outcome")
        if status.get("experience_entries", 0) == 0:
            actions.append("Record first project experience")

        return {
            "request": request,
            "health": health,
            "confidence": confidence,
            "risk": risk,
            "recommended_actions": actions,
        }
