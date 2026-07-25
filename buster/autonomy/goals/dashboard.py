from __future__ import annotations

from typing import Any, Dict, List, Optional
from buster.autonomy.goals.registry import GoalRegistry


class GoalDashboard:
    """Generates structured intent status and summary data for Mission Control UI."""

    def __init__(self, registry: Optional[GoalRegistry] = None):
        self.registry = registry or GoalRegistry()

    def get_dashboard_summary(self) -> Dict[str, Any]:
        all_goals = self.registry.all_goals()

        active: List[Dict[str, Any]] = []
        waiting_approval: List[Dict[str, Any]] = []
        queued: List[Dict[str, Any]] = []
        completed: List[Dict[str, Any]] = []

        for goal in all_goals:
            status = goal.get("status", "PROPOSED")
            card = {
                "id": goal.get("id"),
                "title": goal.get("title"),
                "target": goal.get("target"),
                "status": status,
                "confidence": goal.get("confidence", 1.0),
                "risk_score": goal.get("risk_score", 0.0),
                "evidence": goal.get("evidence", {}),
                "history_length": len(goal.get("history", [])),
                "last_updated": goal.get("updated_at"),
            }

            if status in {"EXECUTING", "IN_PROGRESS"}:
                active.append(card)
            elif status in {"PROPOSED", "WAITING_APPROVAL"}:
                waiting_approval.append(card)
            elif status in {"APPROVED", "QUEUED"}:
                queued.append(card)
            elif status == "COMPLETED":
                completed.append(card)

        return {
            "counts": {
                "active": len(active),
                "waiting_approval": len(waiting_approval),
                "queued": len(queued),
                "completed": len(completed),
                "total": len(all_goals),
            },
            "active_goals": active,
            "waiting_approval": waiting_approval,
            "queued_goals": queued,
            "recent_completed": completed[-5:],
        }