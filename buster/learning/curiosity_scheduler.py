from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from buster.learning.curiosity_evaluator import CuriosityEvaluator, CuriosityTarget
from buster.rhythm.rhythm import LifeState

logger = logging.getLogger(__name__)


@dataclass
class ExplorationTask:
    task_id: str
    target_path: str
    curiosity_score: float
    reasons: List[str]
    execution_class: str = "background"
    priority: int = 1  # Low priority for self-initiated exploration


class CuriosityScheduler:
    """Schedules curiosity-driven exploration tasks based on current system rhythm states."""

    # Permitted life states (both as string names and Enum values)
    PERMITTED_STATES = {
        LifeState.LEISURE,
        LifeState.WORK,
        "LEISURE",
        "WORK",
        "LifeState.LEISURE",
        "LifeState.WORK",
    }

    def __init__(
        self,
        evaluator: CuriosityEvaluator,
        rhythm_service: Optional[Any] = None,
        min_score_threshold: float = 5.0,
    ) -> None:
        self.evaluator = evaluator
        self.rhythm_service = rhythm_service
        self.min_score_threshold = min_score_threshold

    def is_exploration_allowed(self, now: Optional[datetime] = None) -> bool:
        """Checks if current rhythm state permits background exploration."""
        if not self.rhythm_service:
            return True

        status: Dict[str, Any] = {}

        # Check direct methods first before inspecting sub-attributes to avoid MagicMock auto-creation traps
        if callable(getattr(self.rhythm_service, "get_blackboard_status", None)):
            status = self.rhythm_service.get_blackboard_status(now=now)
        elif callable(getattr(self.rhythm_service, "get_status", None)):
            status = self.rhythm_service.get_status(now=now)
        elif hasattr(self.rhythm_service, "rhythm") and callable(getattr(self.rhythm_service.rhythm, "get_blackboard_status", None)):
            status = self.rhythm_service.rhythm.get_blackboard_status(now=now)

        state_val = status.get("life_state", "SLEEP") if isinstance(status, dict) else status

        # Extract string representation safely
        if hasattr(state_val, "name"):
            raw_val = state_val.name.upper()
        elif hasattr(state_val, "value"):
            raw_val = str(state_val.value).upper()
        else:
            raw_val = str(state_val).upper().split(".")[-1]

        if raw_val in {"WORK", "LEISURE"}:
            return True

        logger.debug(f"Exploration skipped: current state '{state_val}' is not permitted.")
        return False

    def schedule_exploration(
        self,
        now: Optional[datetime] = None,
        limit: int = 1,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ExplorationTask]:
        """Scans candidate targets and produces exploration tasks if rhythm state permits."""
        if not self.is_exploration_allowed(now=now):
            return []

        targets = self.evaluator.scan_project(limit=limit * 2, context=context)
        tasks: List[ExplorationTask] = []

        for target in targets:
            if len(tasks) >= limit:
                break

            if target.score >= self.min_score_threshold:
                task_id = f"explore_{hash(target.target_path) & 0xFFFFFF:06x}"
                tasks.append(
                    ExplorationTask(
                        task_id=task_id,
                        target_path=target.target_path,
                        curiosity_score=target.score,
                        reasons=target.reasons,
                        execution_class="background",
                        priority=1,
                    )
                )

        return tasks