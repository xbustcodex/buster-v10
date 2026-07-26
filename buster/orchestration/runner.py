# buster/orchestration/runner.py
from __future__ import annotations

import time
from typing import Dict, List, Set, Any
from buster.capabilities.registry import CapabilityRegistry
from buster.capabilities.models import CapabilityExecutionContext, CapabilityResult
from buster.orchestration.models import MissionPlan, MissionTask
from buster.orchestration.context import MissionContext


class MissionRunner:
    """Executes a MissionPlan task by task, respecting dependencies, retries, and context interpolation."""

    def __init__(self, registry: CapabilityRegistry, agent_id: str = "buster-agent") -> None:
        self.registry = registry
        self.agent_id = agent_id

    def run_mission(self, plan: MissionPlan, initial_variables: Dict[str, Any] | None = None) -> MissionContext:
        context = MissionContext(mission_id=plan.mission_id, initial_variables=initial_variables)
        
        completed_tasks: Set[str] = set()
        pending_tasks: List[MissionTask] = list(plan.tasks)
        
        while pending_tasks:
            ready_tasks = [
                t for t in pending_tasks 
                if all(dep in completed_tasks for dep in t.dependencies)
            ]

            if not ready_tasks:
                raise RuntimeError("Deadlock detected in mission task graph: unresolved dependencies remain.")

            for task in ready_tasks:
                success = self._execute_task_with_retries(task, plan.mission_id, context)
                if success:
                    completed_tasks.add(task.task_id)
                    pending_tasks.remove(task)
                else:
                    raise RuntimeError(f"Mission failed at task '{task.task_id}': {context.errors.get(task.task_id, 'Unknown error')}")

        return context

    def _execute_task_with_retries(self, task: MissionTask, mission_id: str, context: MissionContext) -> bool:
        cap_instance = self.registry.get(task.capability_id)
        if not cap_instance:
            context.set_error(task.task_id, f"Capability '{task.capability_id}' not found in registry.")
            return False

        resolved_arguments = context.resolve_value(task.arguments)

        # Include both task required permissions and capability descriptor permissions
        desc = cap_instance.describe()
        all_perms = set(task.required_permissions) | set(desc.required_permissions)
        # Also include any action-specific permissions
        for act in desc.actions:
            if act.name == task.action:
                all_perms.update(act.required_permissions)

        exec_context = CapabilityExecutionContext(
            mission_id=mission_id,
            task_id=task.task_id,
            trace_id=f"trace_{mission_id}_{task.task_id}",
            agent_id=self.agent_id,
            approved_permissions=frozenset(all_perms),
        )

        attempts = task.max_retries + 1
        last_error = ""

        for attempt in range(1, attempts + 1):
            try:
                result: CapabilityResult = cap_instance.execute(task.action, resolved_arguments, exec_context)
                if result.success:
                    context.set_output(task.task_id, result.output)
                    return True
                else:
                    last_error = result.error or "Unknown capability failure"
            except Exception as e:
                last_error = str(e)

            if attempt < attempts:
                time.sleep(0.1 * attempt)

        context.set_error(task.task_id, f"Failed after {attempts} attempts. Last error: {last_error}")
        return False