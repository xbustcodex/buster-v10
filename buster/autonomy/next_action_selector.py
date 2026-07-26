# buster/autonomy/next_action_selector.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from buster.autonomy.observation_engine import Observation
from buster.autonomy.mission_state import Mission, AutonomyPolicy

logger = logging.getLogger(__name__)


@dataclass
class ActionDecision:
    action_type: str  # e.g., "delegate_fixer", "request_approval", "retry_execution", "complete_mission", "continue"
    target_agent: Optional[str]
    reason: str
    requires_intervention: bool = False


class NextActionSelector:
    """Decides Buster's next operational action based on incoming observations, mission state, and policy."""

    def __init__(self) -> None:
        self.failure_counts: Dict[str, int] = {}

    def select_next_action(self, mission: Mission, observation: Observation) -> ActionDecision:
        obs_type = observation.type
        source = observation.source

        logger.info(f"Evaluating next action for mission [{mission.mission_id}] based on observation [{obs_type}]")

        # 1. Test Failure Rule -> Delegate Fixer
        if obs_type == "test.failed":
            failure_key = f"{mission.mission_id}_test_fail"
            self.failure_counts[failure_key] = self.failure_counts.get(failure_key, 0) + 1
            
            # Check repeated identical failure for circuit breaker simulation
            if self.failure_counts[failure_key] >= 3:
                return ActionDecision(
                    action_type="open_circuit",
                    target_agent=None,
                    reason="Repeated identical test failures reached threshold; opening circuit breaker.",
                    requires_intervention=True,
                )

            return ActionDecision(
                action_type="delegate_fixer",
                target_agent="FixerAgent",
                reason=f"Test failure detected from {source}. Delegating to Fixer with focused context.",
            )

        # 2. Permission Failure Rule -> Request Intervention
        if obs_type == "permission.denied":
            return ActionDecision(
                action_type="request_approval",
                target_agent=None,
                reason="Action violated autonomy policy bounds. Halting and requesting human intervention.",
                requires_intervention=True,
            )

        # 3. Transient Timeout -> Resilient Runner Retry
        if obs_type == "execution.timeout":
            return ActionDecision(
                action_type="retry_execution",
                target_agent=None,
                reason="Transient timeout encountered. Invoking Resilient Runner retry backoff.",
            )

        # 4. Success Criteria Verified -> Complete Mission
        if obs_type == "verification.passed":
            return ActionDecision(
                action_type="complete_mission",
                target_agent=None,
                reason="All verification evidence confirmed successfully. Marking mission complete.",
            )

        # Default fallback
        return ActionDecision(
            action_type="continue",
            target_agent=None,
            reason="Standard observation processed. Continuing active workflow.",
        )