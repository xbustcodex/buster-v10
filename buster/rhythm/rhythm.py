from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional


class LifeState(Enum):
    WORK = "WORK"
    LEISURE = "LEISURE"
    SLEEP = "SLEEP"


class BusterRhythm:
    """Circadian and Weekly Rhythm Engine."""

    def __init__(
        self,
        work_start_hour: int = 8,
        downtime_start_hour: int = 16,
        sleep_start_hour: int = 0,
    ) -> None:
        self.work_start_hour = work_start_hour
        self.downtime_start_hour = downtime_start_hour
        self.sleep_start_hour = sleep_start_hour

    def evaluate_state(self, now: Optional[datetime] = None) -> LifeState:
        """Evaluates current system time against Buster's life schedule."""
        now = now or datetime.now()
        day_of_week = now.weekday()  # 0 = Mon, 5 = Sat, 6 = Sun
        hour = now.hour

        # 1. Sleep state: 00:00 - 08:00 daily
        if 0 <= hour < self.work_start_hour:
            return LifeState.SLEEP

        # 2. Weekend wake hours (08:00 - 00:00): Leisure
        if day_of_week in (5, 6):
            return LifeState.LEISURE

        # 3. Weekdays
        if self.work_start_hour <= hour < self.downtime_start_hour:
            return LifeState.WORK
        else:
            return LifeState.LEISURE

    def get_next_transition(self, now: Optional[datetime] = None) -> datetime:
        """Calculates the exact timestamp of the next state transition."""
        now = now or datetime.now()
        state = self.evaluate_state(now)
        day_of_week = now.weekday()

        if state == LifeState.SLEEP:
            target = now.replace(hour=self.work_start_hour, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target

        if state == LifeState.WORK:
            target = now.replace(hour=self.downtime_start_hour, minute=0, second=0, microsecond=0)
            return target

        # State is LEISURE
        if day_of_week in (5, 6):
            # Weekend leisure runs until midnight (sleep start)
            target = (now + timedelta(days=1)).replace(hour=self.sleep_start_hour, minute=0, second=0, microsecond=0)
            return target
        else:
            # Weekday leisure runs 16:00 to 00:00 (sleep start)
            target = (now + timedelta(days=1)).replace(hour=self.sleep_start_hour, minute=0, second=0, microsecond=0)
            return target

    def get_blackboard_status(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Generates the rhythm state payload for Blackboard and Event Bus."""
        now = now or datetime.now()
        state = self.evaluate_state(now)
        next_transition = self.get_next_transition(now)

        return {
            "life_state": state.value,
            "goal_inhibitor_active": state != LifeState.WORK,
            "dream_sandbox_active": state == LifeState.SLEEP,
            "next_transition_at": next_transition.isoformat(),
        }