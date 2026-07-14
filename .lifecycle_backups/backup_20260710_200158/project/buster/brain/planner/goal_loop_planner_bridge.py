from typing import Any, Dict
from buster.mind.work_loop import WorkingMemoryGoalLoop

class GoalLoopPlannerBridge:
    def __init__(self, loop=None):
        self.loop = loop or WorkingMemoryGoalLoop()

    def plan_from_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self.loop.ingest_observation(observation)
        goal = snapshot.get("goals", [{}])[0] if snapshot.get("goals") else {}
        return {
            "should_plan": bool(goal),
            "goal": goal,
            "mission": snapshot.get("mission", {}),
            "companion_context": snapshot.get("companion_context", {}),
        }
