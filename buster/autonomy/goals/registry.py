from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional
from buster.autonomy.goals.models import GoalProposal
from buster.autonomy.goals.storage import GoalStorage
from buster.utils.datetime_utils import utc_now


class GoalRegistry:
    """Registry managing active and historical goals, preventing duplicates and tracking cooldowns."""

    def __init__(self, storage: Optional[GoalStorage] = None):
        self.storage = storage or GoalStorage()
        self._lock = threading.RLock()

    def is_on_cooldown(self, target: str, cooldown_seconds: float = 300.0) -> bool:
        """Checks if a target has been acted upon recently to prevent duplicate goal loops."""
        with self._lock:
            goals = self.storage.load_all()
            now_ts = time.time()

            for g in goals.values():
                if g.get("target") == target and g.get("status") in {"COMPLETED", "EXECUTING", "APPROVED"}:
                    last_executed = float(g.get("last_execution_ts", 0.0))
                    if now_ts - last_executed < cooldown_seconds:
                        return True
            return False

    def register_proposal(self, proposal: GoalProposal, evidence: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            now_str = utc_now().isoformat() if hasattr(utc_now(), "isoformat") else str(utc_now())

            # Convert proposal.created_at to ISO string if it's a datetime object
            created_at_str = (
                proposal.created_at.isoformat()
                if hasattr(proposal.created_at, "isoformat")
                else str(proposal.created_at)
            )

            goal_data = {
                "id": proposal.id,
                "title": proposal.title,
                "request": proposal.request,
                "target": proposal.target,
                "signal_id": proposal.signal_id,
                "status": "PROPOSED",
                "evidence": evidence,
                "priority": "normal",
                "risk_score": 0.0,
                "confidence": 1.0,
                "cooldown_until": None,
                "superseded_by": None,
                "parent_goal_id": None,
                "child_ids": [],
                "history": [{"status": "PROPOSED", "timestamp": now_str}],
                "last_execution_ts": 0.0,
                "created_at": created_at_str,
            }
            self.storage.save_goal(goal_data)
            return goal_data

    def update_status(self, goal_id: str, new_status: str, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            goal = self.storage.get_goal(goal_id)
            if not goal:
                raise KeyError(f"Goal {goal_id} not found in registry.")

            now_str = utc_now().isoformat() if hasattr(utc_now(), "isoformat") else str(utc_now())

            goal["status"] = new_status
            goal["history"].append({"status": new_status, "timestamp": now_str, "result": result or {}})

            if new_status in {"COMPLETED", "EXECUTING"}:
                goal["last_execution_ts"] = time.time()

            self.storage.save_goal(goal)
            return goal

    def get(self, goal_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.storage.get_goal(goal_id)

    def all_goals(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.storage.load_all().values())