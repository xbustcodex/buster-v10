from __future__ import annotations

from typing import Any, Dict, List

from .storage import load_json, save_json, now_iso

GOALS = "data/goals.json"


class GoalManager:
    """Tracks objectives Buster can pursue over time."""

    def __init__(self, path: str = GOALS):
        self.path = path

    def _state(self) -> Dict[str, Any]:
        return load_json(self.path, {"goals": [], "updated": now_iso()})

    def create_goal(self, title: str, description: str = "", priority: float = 0.5, source: str = "user") -> Dict[str, Any]:
        state = self._state()
        goal = {
            "id": f"goal_{len(state.get('goals', [])) + 1}_{int(__import__('time').time())}",
            "title": title,
            "description": description,
            "priority": round(float(priority), 3),
            "source": source,
            "status": "active",
            "progress": 0.0,
            "created": now_iso(),
            "updated": now_iso(),
            "subgoals": [],
        }
        state.setdefault("goals", []).append(goal)
        state["updated"] = now_iso()
        save_json(self.path, state)
        return goal

    def add_subgoal(self, goal_id: str, title: str) -> Dict[str, Any] | None:
        state = self._state()
        for goal in state.get("goals", []):
            if goal.get("id") == goal_id:
                sub = {"title": title, "status": "pending", "created": now_iso()}
                goal.setdefault("subgoals", []).append(sub)
                goal["updated"] = now_iso()
                save_json(self.path, state)
                return sub
        return None

    def update_goal(self, goal_id: str, status: str | None = None, progress: float | None = None) -> Dict[str, Any] | None:
        state = self._state()
        for goal in state.get("goals", []):
            if goal.get("id") == goal_id:
                if status is not None:
                    goal["status"] = status
                if progress is not None:
                    goal["progress"] = max(0.0, min(1.0, float(progress)))
                goal["updated"] = now_iso()
                save_json(self.path, state)
                return goal
        return None

    def active_goals(self) -> List[Dict[str, Any]]:
        goals = self._state().get("goals", [])
        return sorted([g for g in goals if g.get("status") == "active"], key=lambda g: g.get("priority", 0), reverse=True)
