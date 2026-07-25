from __future__ import annotations

from typing import Any, Dict, Optional
from buster.autonomy.goals.registry import GoalRegistry


class MemorySynthesizer:
    """Synthesizes completed goal execution patterns into long-term strategic memory."""

    def __init__(self, registry: Optional[GoalRegistry] = None):
        self.registry = registry or GoalRegistry()
        self.synthesized_memories: Dict[str, Dict[str, Any]] = {}

    def synthesize_completed_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        goal = self.registry.get(goal_id)
        if not goal or goal.get("status") != "COMPLETED":
            return None

        pattern_key = f"pattern_{goal.get('target')}_{goal.get('title')}"
        
        memory_entry = {
            "pattern_key": pattern_key,
            "goal_id": goal_id,
            "title": goal.get("title"),
            "target": goal.get("target"),
            "success": True,
            "evidence": goal.get("evidence", {}),
            "execution_history": goal.get("history", []),
            "confidence_boost": 0.05,
        }

        self.synthesized_memories[pattern_key] = memory_entry
        return memory_entry

    def get_pattern_experience(self, target: str) -> Optional[Dict[str, Any]]:
        for memory in self.synthesized_memories.values():
            if memory.get("target") == target:
                return memory
        return None