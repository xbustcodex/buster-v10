from __future__ import annotations
from typing import Any, Dict
from buster.living.event_bridge import MissionTimelineEventBridge
from buster.living.mission_events import MissionEventType

class TimelinePlannerBridge:
    """Publishes planner decisions directly to the live mission timeline."""
    def __init__(self):
        self.bridge = MissionTimelineEventBridge()
    def mission_created(self, mission: str, confidence: float = 0.0, risk: str = "unknown", reason: str = "") -> Dict[str, Any]:
        return self.bridge.handle({"type": MissionEventType.PLANNER_CREATED_MISSION, "payload": {"message": f"created mission: {mission}", "mission": mission, "confidence": confidence, "risk": risk, "details": {"reason": reason}}})
    def agent_step(self, agent: str, message: str, confidence: float | None = None, risk: str = "unknown") -> Dict[str, Any]:
        return self.bridge.handle({"type": f"agent.{agent.lower()}.step", "payload": {"agent": agent, "source": agent, "message": message, "confidence": confidence, "risk": risk}})
