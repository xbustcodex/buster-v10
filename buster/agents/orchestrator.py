"""
Multi-Agent Orchestrator for Buster v10.7
Delegates high-level goals into sub-tasks and routes them to specialized worker agents.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("buster.agents.orchestrator")


class MultiAgentOrchestrator:
    """Central manager that coordinates workloads across transient worker agents."""

    def __init__(
        self,
        agent_manager: Optional[Any] = None,
        task_scheduler: Optional[Any] = None,
        event_bus: Optional[Any] = None,
        memory: Optional[Any] = None,
        **kwargs
    ):
        self.agent_manager = agent_manager
        self.task_scheduler = task_scheduler
        self.event_bus = event_bus
        self.memory = memory
        self.active_workflows: Dict[str, Dict[str, Any]] = {}

    def run(self, goal_description: str, *args, **kwargs) -> Any:
        """Synchronous bridge for runtime callers expecting .run()."""
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(self.delegate_goal(str(goal_description)))
        except RuntimeError:
            return asyncio.run(self.delegate_goal(str(goal_description)))

    def execute(self, goal_description: str, *args, **kwargs) -> Any:
        """Alias for .run() to support alternative dispatcher interfaces."""
        return self.run(goal_description, *args, **kwargs)

    async def delegate_goal(self, goal_description: str) -> str:
        """Breaks down a goal and assigns it to appropriate agents."""
        workflow_id = f"WF-{uuid.uuid4().hex[:6]}"
        logger.info(f"Initiating workflow {workflow_id} for goal: '{goal_description}'")

        sub_tasks = self._parse_sub_tasks(goal_description)
        
        self.active_workflows[workflow_id] = {
            "goal": goal_description,
            "status": "IN_PROGRESS",
            "tasks": sub_tasks,
            "completed_tasks": []
        }

        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish("orchestrator:workflow_started", {"workflow_id": workflow_id})

        if self.task_scheduler and hasattr(self.task_scheduler, "schedule"):
            for task in sub_tasks:
                self._assign_task_to_agent(workflow_id, task)
        else:
            logger.warning("No active task_scheduler provided. Task assignment deferred.")

        return workflow_id

    def _parse_sub_tasks(self, goal_description: str) -> List[Dict[str, str]]:
        """Simulated LLM task breakdown."""
        return [
            {"id": "step1", "role": "researcher", "instruction": "Analyze goal context."},
            {"id": "step2", "role": "builder", "instruction": "Execute primary action."},
            {"id": "step3", "role": "tester", "instruction": "Verify successful execution."}
        ]

    def _assign_task_to_agent(self, workflow_id: str, task: Dict[str, str]) -> None:
        """Finds an idle agent with the matching role and schedules the task."""
        required_role = task.get("role", "builder")
        assigned_agent_id = None

        if self.agent_manager and hasattr(self.agent_manager, "agents"):
            for agent_id, descriptor in self.agent_manager.agents.items():
                if descriptor.get("role") == required_role and descriptor.get("state") == "IDLE":
                    assigned_agent_id = agent_id
                    descriptor["state"] = "WORKING"
                    break

        if not assigned_agent_id:
            logger.warning(f"No available agent found for role '{required_role}'. Using fallback.")
            assigned_agent_id = "system_fallback"

        async def agent_execution_wrapper():
            logger.info(f"Agent '{assigned_agent_id}' executing: {task['instruction']}")
            await asyncio.sleep(1)
            
            if self.event_bus and hasattr(self.event_bus, "publish"):
                self.event_bus.publish(
                    "orchestrator:task_completed", 
                    {"workflow_id": workflow_id, "task_id": task["id"], "agent_id": assigned_agent_id}
                )
            
            if self.agent_manager and hasattr(self.agent_manager, "agents"):
                if assigned_agent_id in self.agent_manager.agents:
                    self.agent_manager.agents[assigned_agent_id]["state"] = "IDLE"
            
            return True

        if self.task_scheduler and hasattr(self.task_scheduler, "schedule"):
            self.task_scheduler.schedule(
                name=f"Workflow_{workflow_id}_{task['id']}",
                agent_id=assigned_agent_id,
                coro_func=agent_execution_wrapper
            )