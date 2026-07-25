from __future__ import annotations

from buster.autonomy.goals.capabilities import Capability, CapabilityPolicy, ExecutionPermission
from buster.autonomy.goals.models import GoalEvaluation, GoalProposal


class ApprovalPolicy:
    """Evaluates risk, value, and capability permissions to govern autonomous goal execution."""

    def __init__(self, capability_policy: CapabilityPolicy | None = None):
        self.capability_policy = capability_policy or CapabilityPolicy()

    def determine_capability(self, proposal: GoalProposal) -> Capability:
        title = proposal.title.lower()
        request = proposal.request.lower()

        if "delete" in title or "remove" in request:
            return Capability.DELETE_FILES
        if "commit" in title or "git commit" in request:
            return Capability.GIT_COMMIT
        if "push" in title or "git push" in request:
            return Capability.GIT_PUSH
        if "desktop" in title or "click" in request:
            return Capability.DESKTOP_CONTROL
        # Low-risk maintenance / indexing tasks map to READ_FILES for auto-approval
        if "rebuild" in title or "index" in title or "read" in request:
            return Capability.READ_FILES
        if "write" in title or "update" in request:
            return Capability.WRITE_FILES

        return Capability.READ_FILES

    def evaluate(self, proposal: GoalProposal) -> GoalEvaluation:
        capability = self.determine_capability(proposal)
        permission = self.capability_policy.get_permission(capability)

        if permission == ExecutionPermission.AUTO_APPROVE:
            approved = True
            reason = f"Capability {capability.value} is set to AUTO_APPROVE."
            risk = 0.1
        else:
            approved = False
            reason = f"Capability {capability.value} requires user authorization ({permission.value})."
            risk = 0.6

        return GoalEvaluation(
            goal_id=proposal.id,
            value_score=0.8,
            risk_score=risk,
            cost_score=0.1,
            confidence=0.9,
            is_approved=approved,
            reason=reason,
        )