from typing import Any, Dict, List
from .mission_context import MissionContextManager
from .goal_loop import GoalLoop
from .context_priority import ContextPrioritizer
from .companion_context import CompanionContextBuilder

class WorkingMemoryGoalLoop:
    def __init__(self):
        self.missions = MissionContextManager()
        self.goals = GoalLoop()
        self.prioritizer = ContextPrioritizer()
        self.companion = CompanionContextBuilder()
        self.focus_items: List[Dict[str, Any]] = []

    def start_mission(self, title: str, priority: int = 5) -> Dict[str, Any]:
        return self.missions.start(title, priority=priority).to_dict()

    def ingest_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        goal = self.goals.observe(observation)
        focus = dict(observation)
        focus.setdefault("priority", goal.priority if goal else observation.get("priority", 4))
        self.focus_items.append(focus)
        if goal:
            self.missions.attach_goal(goal.goal_id)
            self.missions.set_focus(goal.title)
        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        focus = self.prioritizer.top(self.focus_items, limit=8)
        goals = self.prioritizer.top(self.goals.active_goals(), limit=8)
        mission = self.missions.snapshot()
        return {
            "mission": mission,
            "goals": goals,
            "focus": focus,
            "companion_context": self.companion.build(mission, goals, focus),
        }
