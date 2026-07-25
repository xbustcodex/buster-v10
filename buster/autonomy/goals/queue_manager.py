from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from buster.autonomy.goals.registry import GoalRegistry


PRIORITY_WEIGHTS = {
    "CRITICAL": 100,
    "HIGH": 75,
    "NORMAL": 50,
    "LOW": 25,
}


class GoalQueueManager:
    """Handles queue prioritization, sorting, and retention cleanup for registered goals."""

    def __init__(self, registry: Optional[GoalRegistry] = None):
        self.registry = registry or GoalRegistry()

    def get_prioritized_queue(self) -> List[Dict[str, Any]]:
        """Returns pending/proposed goals sorted by priority weight (desc) and confidence (desc)."""
        all_goals = self.registry.all_goals()
        pending = [g for g in all_goals if g.get("status") in {"PROPOSED", "PENDING"}]

        def sort_key(goal: Dict[str, Any]):
            priority_str = str(goal.get("priority", "NORMAL")).upper()
            weight = PRIORITY_WEIGHTS.get(priority_str, 50)
            confidence = float(goal.get("confidence", 1.0))
            return (weight, confidence)

        return sorted(pending, key=sort_key, reverse=True)

    def garbage_collect_stale_goals(self, max_age_seconds: float = 86400.0) -> Dict[str, Any]:
        """Purges old COMPLETED or REJECTED goals older than max_age_seconds."""
        all_goals = self.registry.all_goals()
        now_ts = time.time()
        purged_count = 0
        retained_goals = {}

        for g in all_goals:
            status = g.get("status")
            last_ts = float(g.get("last_execution_ts", 0.0))

            if status in {"COMPLETED", "REJECTED"} and (now_ts - last_ts) > max_age_seconds:
                purged_count += 1
            else:
                retained_goals[g["id"]] = g

        self.registry.storage.save_all(retained_goals)

        return {
            "status": "success",
            "purged_count": purged_count,
            "retained_count": len(retained_goals),
        }