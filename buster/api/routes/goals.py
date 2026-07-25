from __future__ import annotations

from typing import Any, Dict, Optional
from buster.autonomy.goals.capabilities import Capability, CapabilityPolicy, ExecutionPermission
from buster.autonomy.goals.dashboard import GoalDashboard
from buster.autonomy.goals.registry import GoalRegistry


class GoalsAPIController:
    """REST API controller handling goal operations without hard framework dependencies."""

    def __init__(
        self,
        registry: Optional[GoalRegistry] = None,
        dashboard: Optional[GoalDashboard] = None,
        capability_policy: Optional[CapabilityPolicy] = None,
    ):
        self.registry = registry or GoalRegistry()
        self.dashboard = dashboard or GoalDashboard(registry=self.registry)
        self.capability_policy = capability_policy or CapabilityPolicy()

    def list_goals(self) -> Dict[str, Any]:
        """GET /api/v1/goals"""
        return {"goals": self.registry.all_goals()}

    def get_dashboard(self) -> Dict[str, Any]:
        """GET /api/v1/goals/dashboard"""
        return self.dashboard.get_dashboard_summary()

    def get_capabilities(self) -> Dict[str, str]:
        """GET /api/v1/goals/capabilities"""
        return {cap.value: perm.value for cap, perm in self.capability_policy.matrix.items()}

    def update_capability_policy(self, capability: str, permission: str) -> Dict[str, Any]:
        """POST /api/v1/goals/capabilities"""
        try:
            cap_enum = Capability(capability.upper())
            perm_enum = ExecutionPermission(permission.upper())
        except ValueError as e:
            return {"status": "error", "message": f"Invalid capability or permission: {str(e)}"}

        self.capability_policy.matrix[cap_enum] = perm_enum
        return {
            "status": "success",
            "capability": cap_enum.value,
            "new_permission": perm_enum.value,
        }

    def decide_goal(self, goal_id: str, action: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """POST /api/v1/goals/{goal_id}/decide"""
        goal = self.registry.get(goal_id)
        if not goal:
            return {"status": "error", "message": f"Goal {goal_id} not found"}

        action_upper = action.upper()
        if action_upper == "APPROVE":
            new_status = "APPROVED"
        elif action_upper == "REJECT":
            new_status = "REJECTED"
        else:
            return {"status": "error", "message": "Action must be APPROVE or REJECT"}

        updated = self.registry.update_status(
            goal_id=goal_id,
            new_status=new_status,
            result={"manual_action": action_upper, "reason": reason or "Human intervention"},
        )
        return {"status": "success", "goal": updated}