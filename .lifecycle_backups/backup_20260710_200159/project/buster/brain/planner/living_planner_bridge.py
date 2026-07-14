from __future__ import annotations

from typing import Any, Dict

from buster.living.engine import LivingOSEngine


class LivingPlannerBridge:
    """
    Connects planner output to the Living OS layer.

    Use this after a planner/intelligence decision to update Mission Control,
    face expression, notification state, and timeline together.
    """

    def __init__(self):
        self.engine = LivingOSEngine()

    def publish_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        mission = plan.get("mission") or plan.get("task") or plan.get("intent") or "New mission"
        confidence = float(plan.get("confidence", 0.0))
        risk = plan.get("risk", "unknown")
        reason = plan.get("reason") or plan.get("why") or "Planner selected this action."
        return self.engine.set_mission(str(mission), confidence=confidence, risk=str(risk), reason=str(reason))

    def publish_agent_step(self, agent: str, message: str, **metadata: Any) -> Dict[str, Any]:
        return self.engine.agent_update(agent, message, **metadata)
