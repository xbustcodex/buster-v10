from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from buster.autonomy.goals.approval_policy import ApprovalPolicy
from buster.autonomy.goals.models import (
    CuriositySignal,
    GoalEvaluation,
    GoalExecutionResult,
    GoalProposal,
)


class GoalService:
    def __init__(self, runtime_core: Optional[Any] = None):
        self.runtime_core = runtime_core
        self.policy = ApprovalPolicy()
        self.signals: Dict[str, CuriositySignal] = {}
        self.proposals: Dict[str, GoalProposal] = {}
        self.evaluations: Dict[str, GoalEvaluation] = {}
        self.statuses: Dict[str, str] = {}

    def observe_and_signal(
        self, signal_type: str, target: str, metadata: Optional[Dict[str, Any]] = None
    ) -> CuriositySignal:
        signal = CuriositySignal(
            signal_type=signal_type, target=target, metadata=metadata or {}
        )
        self.signals[signal.signal_id] = signal
        return signal

    def propose_goal_from_signal(self, signal: CuriositySignal) -> GoalProposal:
        title = f"Rebuild stale project index" if "index" in signal.signal_type else f"Investigate {signal.signal_type}"
        request = f"Scan and update index file at {signal.target}"
        
        proposal = GoalProposal(
            title=title,
            request=request,
            target=signal.target,
            signal_id=signal.signal_id,
        )
        self.proposals[proposal.id] = proposal
        self.statuses[proposal.id] = "PROPOSED"
        return proposal

    def evaluate_proposal(self, proposal: GoalProposal) -> GoalEvaluation:
        evaluation = self.policy.evaluate(proposal)
        self.evaluations[proposal.id] = evaluation
        self.statuses[proposal.id] = "APPROVED" if evaluation.is_approved else "REJECTED"
        return evaluation

    def execute_approved_goal(self, proposal: GoalProposal) -> GoalExecutionResult:
        if self.statuses.get(proposal.id) != "APPROVED":
            raise PermissionError(f"Goal {proposal.id} is not approved for execution.")

        self.statuses[proposal.id] = "EXECUTING"

        # Execute indexing logic safely via target workspace
        target_path = Path(proposal.target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps({"status": "indexed", "updated": True}), encoding="utf-8")

        self.statuses[proposal.id] = "COMPLETED"
        return GoalExecutionResult(
            goal_id=proposal.id,
            success=True,
            output={"index_path": str(target_path)},
        )

    def get_goal_status(self, goal_id: str) -> str:
        return self.statuses.get(goal_id, "UNKNOWN")

    def status(self) -> Dict[str, Any]:
        return {
            "total_signals": len(self.signals),
            "total_proposals": len(self.proposals),
            "statuses": self.statuses,
        }