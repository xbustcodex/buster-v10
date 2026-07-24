from __future__ import annotations

from typing import Dict, Any, List


class NaturalConversationEngine:
    def __init__(self) -> None:
        self.openers = {
            "mission_started": "I've started the mission.",
            "planner_created": "I've created a plan.",
            "tests_failed": "The Tester found a problem.",
            "fix_started": "I'm asking the Fixer to investigate.",
            "mission_complete": "Mission complete.",
            "learning_recorded": "I learned something useful from this.",
        }

    def respond_to_event(self, event: Dict[str, Any]) -> str:
        key = str(event.get("event") or event.get("type") or "").lower()
        base = self.openers.get(key, event.get("title") or "I've updated the mission.")
        detail = event.get("message") or event.get("summary") or ""
        confidence = event.get("confidence")
        risk = event.get("risk")
        extras: List[str] = []
        if confidence is not None:
            try:
                extras.append(f"Confidence is {float(confidence) * 100:.0f}%.")
            except Exception:
                pass
        if risk:
            extras.append(f"Risk is {risk}.")
        return " ".join([p for p in [base, detail, *extras] if p]).strip()

    def answer_why(self, context: Dict[str, Any]) -> str:
        reason = context.get("reason") or context.get("why") or "it matched the safest current strategy"
        action = context.get("action") or "that action"
        confidence = context.get("confidence")
        if confidence is not None:
            try:
                return f"I did {action} because {reason}. My confidence was {float(confidence) * 100:.0f}%."
            except Exception:
                pass
        return f"I did {action} because {reason}."

    def idle_checkin(self, status: Dict[str, Any]) -> str:
        mission = status.get("current_mission") or "no active mission"
        active_agents = status.get("active_agents", 0)
        return f"I'm still here. Current mission: {mission}. Active agents: {active_agents}."