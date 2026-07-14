
from __future__ import annotations

from typing import Dict, Any

from buster.collaboration.engine import CollaborativeAgentEngine


class CollaborationPlannerBridge:
    def __init__(self, engine: CollaborativeAgentEngine | None = None):
        self.engine = engine or CollaborativeAgentEngine()

    def announce_plan(self, mission: str, confidence: float = 0.0, risk: str = "unknown") -> Dict[str, Any]:
        return self.engine.set_agent_state("Planner", "planning", f"Mission created: {mission}", confidence=confidence, risk=risk, mission_id=mission, talk=True)

    def announce_decision(self, agent: str, decision: str, reason: str, confidence: float, risk: str = "unknown") -> Dict[str, Any]:
        message = f"{decision} Reason: {reason}"
        return self.engine.set_agent_state(agent, "thinking", message, confidence=confidence, risk=risk, mission_id="decision", talk=True)
