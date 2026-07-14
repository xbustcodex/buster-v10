from __future__ import annotations

from typing import Any, Dict, Optional

from buster.autonomy.engine import AutonomyEngine


class AutonomyPlanner:
    """Planner bridge for Jarvis-style natural language commands."""

    def __init__(self, engine: Optional[AutonomyEngine] = None) -> None:
        self.engine = engine or AutonomyEngine()

    def plan_next(self, request: str, project_type: str = "general", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        decision = self.engine.decide_next_action(request, project_type=project_type, context=context)
        return {
            "request": request,
            "project_type": project_type,
            "next_action": decision.recommended_action,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "strategy": decision.strategy,
            "plugins": decision.plugins,
            "patterns": decision.patterns,
        }

    def queue_autonomous_job(self, title: str, request: str, project: str = "default", project_type: str = "general") -> Dict[str, Any]:
        job = self.engine.create_job(title=title, request=request, project=project, project_type=project_type)
        return job.to_dict()
