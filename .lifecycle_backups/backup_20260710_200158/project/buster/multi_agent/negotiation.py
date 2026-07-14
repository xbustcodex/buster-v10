from __future__ import annotations
from typing import Dict, List
from .blackboard import CollaborationBlackboard

class AgentNegotiator:
    def __init__(self, blackboard: CollaborationBlackboard) -> None:
        self.blackboard = blackboard

    def negotiate(self, mission: str, candidate_agents: List[str]) -> Dict[str, object]:
        if not candidate_agents:
            raise ValueError("candidate_agents cannot be empty")
        scores = {}
        mission_l = mission.lower()
        for agent in candidate_agents:
            score = 0.5
            if agent == "tester" and ("test" in mission_l or "regression" in mission_l): score += 0.3
            if agent == "fixer" and ("fix" in mission_l or "failure" in mission_l or "regression" in mission_l): score += 0.3
            if agent == "builder" and ("build" in mission_l or "compile" in mission_l): score += 0.25
            if agent == "learning" and ("record" in mission_l or "strategy" in mission_l): score += 0.25
            scores[agent] = min(score, 0.99)
        chosen = max(scores, key=scores.get)
        decision = self.blackboard.decide(mission=mission, chosen_agent=chosen, reason=f"{chosen} has the strongest match for this mission step.", confidence=scores[chosen], next_agents=[a for a in candidate_agents if a != chosen])
        return {"decision": decision.to_dict(), "scores": scores}
