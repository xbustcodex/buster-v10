from __future__ import annotations

from typing import Any, Dict

from buster.mind import MindEngine


class MindPlannerBridge:
    """Gives planners access to attention, working memory, goals, and curiosity."""

    def __init__(self, mind: MindEngine | None = None):
        self.mind = mind or MindEngine()

    def prepare_planning_context(self) -> Dict[str, Any]:
        thought = self.mind.think()
        return {
            "focus": thought.get("attention", {}).get("current_focus"),
            "working_memory": thought.get("working_memory"),
            "active_goals": thought.get("active_goals", []),
            "curiosity_suggestions": thought.get("curiosity_suggestions", []),
        }

    def should_act_now(self) -> bool:
        ctx = self.prepare_planning_context()
        focus = ctx.get("focus") or {}
        return float(focus.get("priority", 0)) >= 0.72
