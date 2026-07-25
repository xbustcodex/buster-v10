from __future__ import annotations

from typing import Any, Dict, List, Optional
from buster.autonomy.goals.goal_service import GoalService
from buster.autonomy.goals.registry import GoalRegistry


class CuriosityBridge:
    """Connects Curiosity Engine observations to the Goal Runtime via runtime ticks."""

    def __init__(self, goal_service: GoalService, registry: Optional[GoalRegistry] = None):
        self.goal_service = goal_service
        self.registry = registry or GoalRegistry()

    def process_observation(
        self, signal_type: str, target: str, metadata: Optional[Dict[str, Any]] = None, cooldown_seconds: float = 300.0
    ) -> Optional[Dict[str, Any]]:
        """Processes an observation: checks cooldowns, emits a signal, and generates a proposal if fresh."""
        if self.registry.is_on_cooldown(target, cooldown_seconds=cooldown_seconds):
            return None

        # 1. Create curiosity signal
        signal = self.goal_service.observe_and_signal(
            signal_type=signal_type, target=target, metadata=metadata or {}
        )

        # 2. Convert signal to goal proposal
        proposal = self.goal_service.propose_goal_from_signal(signal)

        # 3. Register in persistent storage with evidence
        registered_goal = self.registry.register_proposal(proposal, evidence=metadata or {})

        return registered_goal