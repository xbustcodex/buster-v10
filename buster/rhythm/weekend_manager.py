from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from buster.rhythm.rhythm import LifeState

logger = logging.getLogger(__name__)


class WeekendRhythmManager:
    """Manages weekend schedule shifts (Saturday/Sunday) and 16-hour downtime lockouts."""

    def __init__(self, start_hour: int = 8, leisure_hours: int = 16) -> None:
        self.start_hour = start_hour
        self.leisure_hours = leisure_hours

    def is_weekend(self, dt: Optional[datetime] = None) -> bool:
        target_dt = dt or datetime.now()
        # Monday=0, Sunday=6 -> Saturday(5) and Sunday(6)
        return target_dt.weekday() in (5, 6)

    def evaluate_weekend_state(self, dt: Optional[datetime] = None) -> Dict[str, Any]:
        target_dt = dt or datetime.now()
        if not self.is_weekend(target_dt):
            return {
                "is_weekend": False,
                "override_state": None,
                "work_inhibited": False,
                "deep_dream_eligible": False,
            }

        hour = target_dt.hour
        end_hour = self.start_hour + self.leisure_hours

        # Handle windows that don't cross midnight vs windows that wrap past midnight
        if end_hour <= 24:
            is_leisure = self.start_hour <= hour < end_hour
        else:
            wrapped_end = end_hour % 24
            is_leisure = hour >= self.start_hour or hour < wrapped_end

        if is_leisure:
            return {
                "is_weekend": True,
                "override_state": LifeState.LEISURE,
                "work_inhibited": True,
                "deep_dream_eligible": False,
            }

        # Overnight Deep Dream Window
        return {
            "is_weekend": True,
            "override_state": LifeState.SLEEP,
            "work_inhibited": True,
            "deep_dream_eligible": True,
        }