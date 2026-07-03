from __future__ import annotations

from typing import Dict, Any

try:
    from buster.conversation_os import ConversationOS
except Exception:  # pragma: no cover
    ConversationOS = None  # type: ignore


class ConversationPlannerBridge:
    def __init__(self) -> None:
        if ConversationOS is None:
            raise RuntimeError("ConversationOS is not available")
        self.conversation = ConversationOS()

    def announce_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "event": "planner_created",
            "actor": "Planner",
            "title": "Planner created a mission plan",
            "message": plan.get("summary") or plan.get("goal") or "I have a strategy ready.",
            "confidence": plan.get("confidence"),
            "risk": plan.get("risk"),
            "priority": "important",
        }
        return self.conversation.mission_event(event)

    def explain_plan(self, plan: Dict[str, Any]) -> str:
        return self.conversation.why({
            "action": plan.get("strategy") or "this plan",
            "reason": plan.get("reason") or "it best matches the current mission context and past experience",
            "confidence": plan.get("confidence"),
        })
