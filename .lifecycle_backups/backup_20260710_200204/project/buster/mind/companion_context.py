from typing import Any, Dict, List

class CompanionContextBuilder:
    def build(self, mission: Dict[str, Any], goals: List[Dict[str, Any]], focus: List[Dict[str, Any]]) -> Dict[str, Any]:
        active_goal = goals[0] if goals else None
        return {
            "mode": "companion",
            "mission": mission,
            "active_goal": active_goal,
            "focus": focus,
            "suggested_speech": self.suggest_speech(mission, active_goal, focus),
        }

    def suggest_speech(self, mission: Dict[str, Any], goal: Dict[str, Any] | None, focus: List[Dict[str, Any]]) -> str:
        if goal:
            return f"I noticed something useful: {goal.get('title')}. {goal.get('next_action', '')}"
        if mission:
            return f"I'm tracking the mission: {mission.get('title', 'current work')}."
        if focus:
            return "I'm watching the important workspace signals and will speak only if something useful happens."
        return "I'm here and monitoring quietly."
