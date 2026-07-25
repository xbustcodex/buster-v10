from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from buster.autonomy.goals.registry import GoalRegistry


class BrainState(Enum):
    OBSERVING = "OBSERVING"
    SCANNING = "SCANNING"
    THINKING = "THINKING"
    WAITING = "WAITING"


class IdleBrain:
    """Manages background thinking and proactive heartbeat states when no primary task is active."""

    def __init__(self, registry: Optional[GoalRegistry] = None):
        self.registry = registry or GoalRegistry()
        self.current_state = BrainState.WAITING
        self.tick_count = 0

    def evaluate_next_state(self, active_tasks_count: int = 0) -> BrainState:
        """Determines idle brain state based on runtime activity and tick cycles."""
        # If system is actively working on primary jobs, stay out of the way
        if active_tasks_count > 0:
            self.current_state = BrainState.WAITING
            return self.current_state

        # Increment idle ticks only when actually idle
        self.tick_count += 1

        # Proactive rotation on idle ticks
        cycle = self.tick_count % 3
        if cycle == 1:
            self.current_state = BrainState.OBSERVING
        elif cycle == 2:
            self.current_state = BrainState.SCANNING
        else:
            self.current_state = BrainState.THINKING

        return self.current_state

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.current_state.value,
            "tick_count": self.tick_count,
            "is_idle": self.current_state != BrainState.WAITING,
        }