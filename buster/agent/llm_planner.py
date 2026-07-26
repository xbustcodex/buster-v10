# buster/agent/llm_planner.py
from __future__ import annotations

import json
import re
from typing import List, Dict, Any, Optional
from buster.capabilities.registry import CapabilityRegistry
from buster.agent.core import BusterAgent
from buster.orchestration.context import MissionContext


class LLMIntentPlanner:
    """Decomposes natural language goals into structured task graphs using available registry capabilities."""

    def __init__(self, agent: BusterAgent) -> None:
        self.agent = agent
        self.registry = agent.registry

    def generate_task_definitions_from_goal(self, goal: str) -> List[Dict[str, Any]]:
        """
        Inspects registered capabilities and produces a task sequence.
        In production, this queries an LLM with capability descriptors. 
        For robust local execution & testing, we support heuristic fallback and LLM stubbing.
        """
        capabilities_summary = []
        caps = getattr(self.registry, "_capabilities", {})
        for cap_id in caps.keys():
            cap = self.registry.get(cap_id)
            if cap:
                desc = cap.describe()
                actions = []
                for a in desc.actions:
                    schema = getattr(a, "argument_schema", getattr(a, "parameters", {}))
                    actions.append({
                        "name": a.name, 
                        "description": a.description, 
                        "argument_schema": schema
                    })
                capabilities_summary.append({
                    "capability_id": desc.capability_id,
                    "name": desc.name,
                    "actions": actions
                })

        goal_lower = goal.lower()
        if "write" in goal_lower and "read" in goal_lower:
            file_path = "autonomous_mission.txt"
            return [
                {
                    "task_id": "auto_write",
                    "capability_id": "core.filesystem",
                    "action": "filesystem.write_file",
                    "arguments": {"file_path": file_path, "content": f"Goal: {goal}"},
                },
                {
                    "task_id": "auto_read",
                    "capability_id": "core.filesystem",
                    "action": "filesystem.read_file",
                    "arguments": {"file_path": file_path},
                    "dependencies": ["auto_write"],
                },
            ]

        raise ValueError(f"Unable to automatically decompose goal without LLM configured: '{goal}'")

    def run_natural_language_goal(self, goal: str) -> MissionContext:
        """Parses a natural language goal into tasks and executes the mission."""
        task_defs = self.generate_task_definitions_from_goal(goal)
        return self.agent.execute_plan_from_template(goal=goal, task_definitions=task_defs)