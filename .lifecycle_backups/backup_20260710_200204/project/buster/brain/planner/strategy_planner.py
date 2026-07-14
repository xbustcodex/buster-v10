from __future__ import annotations

from typing import Any, Dict

from buster.learning import LearningEngine
from buster.plugins.registry import PluginRegistry


class StrategyPlanner:
    """Planner bridge between Buster Brain, Learning Engine and Plugins."""

    def __init__(self, learning: LearningEngine | None = None, registry: PluginRegistry | None = None) -> None:
        self.learning = learning or LearningEngine()
        self.registry = registry or PluginRegistry()

    def plan(self, request: str, project_type: str = "general") -> Dict[str, Any]:
        recommendation = self.learning.recommend_strategy(project_type=project_type, request=request)
        plugins = self.registry.find_by_capability(project_type)

        steps = [
            "Understand user request",
            f"Use strategy: {recommendation['strategy'].get('name')}",
            "Assign agent team",
            "Execute build/test/fix/verify loop",
            "Record outcome in Learning Engine",
        ]
        if plugins:
            steps.insert(2, "Load matching plugins")

        return {
            "request": request,
            "project_type": project_type,
            "recommended_strategy": recommendation["strategy"],
            "reusable_patterns": recommendation["patterns"],
            "similar_experiences": recommendation["similar_experiences"],
            "plugins": plugins,
            "steps": steps,
        }
