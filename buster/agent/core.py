# buster/agent/core.py
from __future__ import annotations

from typing import Dict, Any, List, Optional
from buster.capabilities.registry import CapabilityRegistry
from buster.orchestration.planner import MissionPlanner
from buster.orchestration.runner import MissionRunner
from buster.orchestration.context import MissionContext
from buster.orchestration.models import MissionPlan


class BusterAgent:
    """Central agent core that orchestrates capabilities, planning, and mission execution."""

    def __init__(self, registry: CapabilityRegistry, agent_id: str = "buster-agent-core") -> None:
        self.registry = registry
        self.agent_id = agent_id
        self.planner = MissionPlanner(registry)
        self.runner = MissionRunner(registry, agent_id=agent_id)

    def execute_plan_from_template(self, goal: str, task_definitions: List[Dict[str, Any]], initial_variables: Optional[Dict[str, Any]] = None) -> MissionContext:
        """Plans and executes a structured mission from explicit task definitions."""
        plan: MissionPlan = self.planner.plan_from_template(goal=goal, task_definitions=task_definitions)
        return self.runner.run_mission(plan, initial_variables=initial_variables)