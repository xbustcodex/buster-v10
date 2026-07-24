from __future__ import annotations

from buster.autonomy.goals.models import GoalProposal, GoalEvaluation


class ApprovalPolicy:
    """Evaluates risk, cost, and confidence to govern autonomous goal execution."""

    def evaluate(self, proposal: GoalProposal) -> GoalEvaluation:
        # Default policy: read-only index/maintenance goals are low risk
        if "index" in proposal.title.lower() or "read" in proposal.request.lower():
            risk = 0.05
            value = 0.85
            cost = 0.10
            confidence = 0.95
            approved = True
            reason = "Classified as low-risk maintenance task."
        else:
            risk = 0.50
            value = 0.50
            cost = 0.50
            confidence = 0.70
            approved = False
            reason = "High risk or unknown task; requires explicit human approval."

        return GoalEvaluation(
            goal_id=proposal.id,
            value_score=value,
            risk_score=risk,
            cost_score=cost,
            confidence=confidence,
            is_approved=approved,
            reason=reason,
        )