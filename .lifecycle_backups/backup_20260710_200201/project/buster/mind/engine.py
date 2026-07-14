from __future__ import annotations

from typing import Any, Dict

from .attention_system import AttentionSystem
from .working_memory import WorkingMemory
from .goal_manager import GoalManager
from .curiosity import CuriosityEngine
from .reflection import ReflectionCycle
from .storage import load_json, save_json, now_iso

MIND_STATE = "data/mind_state.json"


class MindEngine:
    """Buster cognitive control layer.

    Perception feeds attention. Important events enter working memory.
    Goals and curiosity guide planning. Reflection improves long-term behaviour.
    """

    def __init__(self):
        self.attention = AttentionSystem()
        self.working_memory = WorkingMemory()
        self.goals = GoalManager()
        self.curiosity = CuriosityEngine()
        self.reflection = ReflectionCycle()

    def perceive(self, source: str, kind: str, title: str, details: str = "", importance: float = 0.5, urgency: float = 0.5, confidence: float = 0.5) -> Dict[str, Any]:
        event = self.attention.observe(source, kind, title, details, importance, urgency, confidence)
        if event.get("focused"):
            self.working_memory.remember("attention_event", title, event, priority=event.get("priority", 0.5))
        self._update_state(last_event=event)
        return event

    def create_goal_from_focus(self) -> Dict[str, Any] | None:
        focus = self.attention.get_state().get("current_focus")
        if not focus:
            return None
        if focus.get("priority", 0) < 0.75:
            return None
        return self.goals.create_goal(
            title=f"Respond to {focus.get('title')}",
            description=focus.get("details", ""),
            priority=focus.get("priority", 0.5),
            source=focus.get("source", "attention"),
        )

    def think(self) -> Dict[str, Any]:
        state = {
            "timestamp": now_iso(),
            "attention": self.attention.get_state(),
            "working_memory": self.working_memory.summary(),
            "active_goals": self.goals.active_goals()[:5],
            "curiosity_suggestions": self.curiosity.suggest_from_memory()[:5],
        }
        save_json(MIND_STATE, state)
        return state

    def reflect(self) -> Dict[str, Any]:
        result = self.reflection.run_daily_reflection()
        self._update_state(last_reflection=result)
        return result

    def _update_state(self, **updates: Any) -> None:
        state = load_json(MIND_STATE, {"created": now_iso()})
        state.update(updates)
        state["updated"] = now_iso()
        save_json(MIND_STATE, state)
