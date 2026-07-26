from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class LifeState(Enum):
    WORK = "Work Mode (High Focus)"
    DOWNTIME = "Downtime (Rest & Casual Reflection)"
    WEEKEND_RELAX = "Weekend Leisure (Low Power)"
    SLEEP = "Sleep Mode (Deep Maintenance & Dreams)"


class BusterRhythm:
    """Circadian and Weekly Rhythm Engine.

    Maps real PC clock time to Buster's cognitive states:
    - Weekdays 08:00 - 16:00 -> WORK (Focus, heavy task execution)
    - Weekdays 16:00 - 00:00 -> DOWNTIME (Low power, open curiosity, banter)
    - Everyday 00:00 - 08:00 -> SLEEP (Dream cycle, sandbox testing, memory consolidation)
    - Weekends (Sat/Sun wake hours) -> WEEKEND_RELAX (16h casual leisure)
    """

    def __init__(
        self,
        work_start_hour: int = 8,
        downtime_start_hour: int = 16,
        sleep_start_hour: int = 0,
    ) -> None:
        self.work_start_hour = work_start_hour
        self.downtime_start_hour = downtime_start_hour
        self.sleep_start_hour = sleep_start_hour
        self.current_state = self.evaluate_state()

    def evaluate_state(self, now: Optional[datetime] = None) -> LifeState:
        """Evaluates current system time against Buster's life schedule."""
        if now is None:
            now = datetime.now()

        day_of_week = now.weekday()  # 0 = Mon, 4 = Fri, 5 = Sat, 6 = Sun
        hour = now.hour

        # 1. Sleep state runs every night 00:00 - 08:00
        if 0 <= hour < self.work_start_hour:
            return LifeState.SLEEP

        # 2. Weekend state (Saturday & Sunday wake hours 08:00 - 00:00)
        if day_of_week in (5, 6):
            return LifeState.WEEKEND_RELAX

        # 3. Weekday state (Monday to Friday)
        if self.work_start_hour <= hour < self.downtime_start_hour:
            return LifeState.WORK
        else:
            return LifeState.DOWNTIME

    def get_blackboard_status(self) -> Dict[str, Any]:
        """Generates status variables for Buster's blackboard state."""
        now = datetime.now()
        state = self.evaluate_state(now)
        self.current_state = state

        return {
            "current_state": state.value,
            "day_of_week": now.strftime("%A"),
            "time": now.strftime("%H:%M:%S"),
            "allow_heavy_tasks": state == LifeState.WORK,
            "goal_inhibitor_active": state in (LifeState.DOWNTIME, LifeState.WEEKEND_RELAX),
            "dream_sandbox_active": state == LifeState.SLEEP,
        }


def run_cli_rhythm() -> None:
    rhythm = BusterRhythm()
    status = rhythm.get_blackboard_status()

    print(f"⏰ System Time: {status['time']} ({status['day_of_week']})")
    print(f"🧠 Cognitive State: {status['current_state']}")
    print(f"🔒 Goal Inhibitor Active: {status['goal_inhibitor_active']}")
    print(f"🌙 Dream Sandbox Active: {status['dream_sandbox_active']}")


if __name__ == "__main__":
    run_cli_rhythm()