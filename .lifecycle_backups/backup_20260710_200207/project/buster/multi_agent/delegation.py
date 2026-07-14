from __future__ import annotations
from typing import Dict, List

class DelegationPlanner:
    DEFAULT_FLOW = ["planner", "memory", "builder", "tester", "fixer", "reviewer", "verifier", "learning"]

    def plan(self, mission: str, intent: str = "general") -> Dict[str, object]:
        mission_l = mission.lower()
        agents: List[str] = list(self.DEFAULT_FLOW)
        if "android" in mission_l or intent == "android_development":
            agents = ["planner", "memory", "world_model", "builder", "tester", "fixer", "verifier", "learning", "conversation"]
        elif "esp32" in mission_l or "arduino" in mission_l or intent == "esp32_development":
            agents = ["planner", "memory", "world_model", "builder", "tester", "fixer", "verifier", "learning", "conversation"]
        elif "test" in mission_l or "fail" in mission_l or intent == "debugging_tests":
            agents = ["planner", "tester", "fixer", "reviewer", "verifier", "learning"]
        return {"mission": mission, "intent": intent, "agents": agents, "first_agent": agents[0], "reason": f"Delegated based on mission intent: {intent}"}
