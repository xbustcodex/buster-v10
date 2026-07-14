from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

@dataclass
class Goal:
    goal_id: str
    title: str
    source: str = "user"
    priority: int = 5
    status: str = "open"
    confidence: float = 0.75
    risk: str = "medium"
    evidence: List[str] = None
    next_action: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.evidence is None:
            self.evidence = []
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class GoalLoop:
    def __init__(self):
        self.goals: Dict[str, Goal] = {}

    def create_goal(self, title: str, source: str = "user", priority: int = 5, evidence: Optional[List[str]] = None) -> Goal:
        goal_id = "goal_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        goal = Goal(goal_id=goal_id, title=title, source=source, priority=priority, evidence=evidence or [])
        goal.next_action = self.recommend_next_action(goal)
        self.goals[goal_id] = goal
        return goal

    def observe(self, observation: Dict[str, Any]) -> Optional[Goal]:
        text = str(observation.get("text") or observation.get("label") or observation.get("event") or "").lower()
        source = str(observation.get("source", "observation"))
        if any(k in text for k in ["error", "failed", "crash", "exception"]):
            return self.create_goal("Investigate and fix detected problem", source=source, priority=9, evidence=[text])
        if any(k in text for k in ["android studio", "esp32", "arduino", "pixel connected", "repository changed"]):
            return self.create_goal("Prepare workspace for detected development context", source=source, priority=7, evidence=[text])
        if any(k in text for k in ["idle", "away", "inactive"]):
            return self.create_goal("Monitor workspace quietly until user returns", source=source, priority=3, evidence=[text])
        return None

    def recommend_next_action(self, goal: Goal) -> str:
        title = goal.title.lower()
        if "fix" in title or "problem" in title:
            return "Ask Fixer Agent to inspect logs and propose repair."
        if "workspace" in title:
            return "Load relevant plugins, index project, and prepare Mission Control."
        if "quietly" in title:
            return "Reduce speech frequency and continue ambient monitoring."
        return "Create mission plan and assign the best available agent."

    def active_goals(self) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self.goals.values() if g.status in ("open", "active")]

    def complete_goal(self, goal_id: str, result: str = "completed") -> bool:
        goal = self.goals.get(goal_id)
        if not goal:
            return False
        goal.status = result
        goal.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return True
