# buster/orchestration/planner.py
from __future__ import annotations

import uuid
from typing import List, Dict, Any
from buster.capabilities.registry import CapabilityRegistry
from buster.orchestration.models import MissionPlan, MissionTask


class MissionPlanner:
    """Deconstructs high-level intents or explicit pipelines into a validated MissionPlan."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def plan_from_template(self, goal: str, task_definitions: List[Dict[str, Any]]) -> MissionPlan:
        mission_id = f"mission_{uuid.uuid4().hex[:8]}"
        plan = MissionPlan(mission_id=mission_id, goal=goal)

        for idx, tdef in enumerate(task_definitions):
            task_id = tdef.get("task_id", f"task_{idx+1}")
            capability_id = tdef.get("capability_id")
            action = tdef.get("action")
            arguments = tdef.get("arguments", {})
            dependencies = tdef.get("dependencies", [])

            # Fetch capability instance and call describe() to get its descriptor
            cap_instance = self.registry.get(capability_id)
            if not cap_instance:
                raise ValueError(f"Capability '{capability_id}' not found in registry during planning.")
            
            desc = cap_instance.describe()

            action_desc = next((a for a in desc.actions if a.name == action), None)
            if not action_desc:
                raise ValueError(f"Action '{action}' not supported by capability '{capability_id}'.")

            task = MissionTask(
                task_id=task_id,
                capability_id=capability_id,
                action=action,
                arguments=arguments,
                dependencies=dependencies,
                required_permissions=frozenset(action_desc.required_permissions),
                risk_level=action_desc.risk_level,
            )
            plan.add_task(task)

        return plan