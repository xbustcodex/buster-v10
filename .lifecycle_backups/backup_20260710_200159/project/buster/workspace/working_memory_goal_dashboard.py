from typing import Any, Dict

class WorkingMemoryGoalDashboard:
    def render_model(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        mission = snapshot.get("mission", {})
        goals = snapshot.get("goals", [])
        focus = snapshot.get("focus", [])
        companion = snapshot.get("companion_context", {})
        return {
            "title": "Working Memory + Goal Loop",
            "mission_title": mission.get("title", "No active mission"),
            "current_focus": mission.get("current_focus", ""),
            "active_goals": len(goals),
            "focus_items": len(focus),
            "speech": companion.get("suggested_speech", ""),
            "goals": goals,
            "focus": focus,
        }
