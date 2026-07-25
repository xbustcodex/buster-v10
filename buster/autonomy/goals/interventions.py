from __future__ import annotations

from typing import Any, Dict, Optional
from buster.autonomy.goals.capabilities import Capability, CapabilityPolicy, ExecutionPermission
from buster.autonomy.goals.models import GoalProposal
from buster.autonomy.goals.registry import GoalRegistry


class HumanInterventionManager:
    """Provides direct operator overrides for pausing, force-queuing, and policy lockdown."""

    def __init__(
        self,
        registry: Optional[GoalRegistry] = None,
        capability_policy: Optional[CapabilityPolicy] = None,
    ):
        self.registry = registry or GoalRegistry()
        self.capability_policy = capability_policy or CapabilityPolicy()
        self.is_system_paused: bool = False

    def toggle_pause(self, pause_state: Optional[bool] = None) -> bool:
        """Flips or sets the emergency pause state."""
        if pause_state is None:
            self.is_system_paused = not self.is_system_paused
        else:
            self.is_system_paused = pause_state
        return self.is_system_paused

    def force_inject_goal(self, title: str, request: str, target: str) -> Dict[str, Any]:
        """Bypasses normal curiosity/cooldown checks to immediately register a manual goal."""
        proposal = GoalProposal(
            title=title,
            request=request,
            target=target,
            signal_id="operator_override",
        )
        return self.registry.register_proposal(
            proposal=proposal,
            evidence={"injected_by": "operator", "priority": "CRITICAL"},
        )

    def emergency_lockdown(self) -> Dict[str, str]:
        """Sets dangerous capabilities to DENY and all others to PROMPT_USER for maximum containment."""
        for cap in Capability:
            if cap in {Capability.DELETE_FILES, Capability.DESKTOP_CONTROL, Capability.GIT_PUSH}:
                self.capability_policy.matrix[cap] = ExecutionPermission.DENY
            else:
                self.capability_policy.matrix[cap] = ExecutionPermission.PROMPT_USER

        return {cap.value: perm.value for cap, perm in self.capability_policy.matrix.items()}