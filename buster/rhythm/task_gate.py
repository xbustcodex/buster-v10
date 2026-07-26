from __future__ import annotations

from typing import Any, Dict, Tuple, Optional


class TaskGate:
    """Central evaluator for task execution approval based on LifeState."""

    @staticmethod
    def evaluate(task_metadata: Dict[str, Any], current_rhythm: Dict[str, Any]) -> Tuple[bool, str]:
        """Evaluates whether a task is allowed to execute given current rhythm state.

        Returns: (is_allowed: bool, reason: str)
        """
        life_state = current_rhythm.get("life_state", "WORK")
        allowed_states = task_metadata.get("allowed_states", ["WORK", "LEISURE", "SLEEP"])
        execution_class = task_metadata.get("execution_class", "background")
        can_override = task_metadata.get("can_override_inhibitor", False)
        maintenance_safe = task_metadata.get("maintenance_safe", False)

        # Explicit state restriction on task
        if life_state not in allowed_states:
            return False, f"Task restricted from state '{life_state}'"

        # WORK Mode: Everything allowed
        if life_state == "WORK":
            return True, "Allowed in WORK state"

        # User-triggered foreground tasks can always override inhibitor
        if execution_class == "foreground" and can_override:
            return True, "User override active"

        # LEISURE Mode: High power/background goals throttled
        if life_state == "LEISURE":
            if execution_class == "background" and task_metadata.get("priority") == "high":
                return False, "Heavy background goals inhibited during LEISURE state"
            return True, "Allowed in LEISURE state"

        # SLEEP Mode: Only maintenance-safe tasks or explicit overrides
        if life_state == "SLEEP":
            if maintenance_safe:
                return True, "Maintenance safe task allowed during SLEEP state"
            return False, "Background task blocked during SLEEP state"

        return False, "Blocked by default task gate policy"