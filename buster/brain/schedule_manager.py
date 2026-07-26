from __future__ import annotations

import datetime
from enum import Enum
from typing import Dict, Any, Optional


class LifeState(Enum):
    WORK = "WORK"
    DOWNTIME = "DOWNTIME"
    SLEEP = "SLEEP"


class ScheduleManager:
    """Manages Buster's 24/7 human schedule, internal clock, and weekend shifts."""

    def __init__(
        self,
        work_start_hour: int = 9,      # 9:00 AM - 5:00 PM (8 Hours)
        downtime_start_hour: int = 17,  # 5:00 PM - 1:00 AM (8 Hours)
        sleep_start_hour: int = 1,      # 1:00 AM - 9:00 AM (8 Hours)
        dnd_mode: bool = False
    ) -> None:
        self.work_start_hour = work_start_hour
        self.downtime_start_hour = downtime_start_hour
        self.sleep_start_hour = sleep_start_hour
        self.dnd_mode = dnd_mode

    def get_current_time(self) -> datetime.datetime:
        """Returns current local system time."""
        return datetime.datetime.now()

    def is_weekend(self, dt: Optional[datetime.datetime] = None) -> bool:
        """Determines if the current day is Saturday (5) or Sunday (6)."""
        dt = dt or self.get_current_time()
        return dt.weekday() in (5, 6)

    def determine_life_state(self, dt: Optional[datetime.datetime] = None) -> LifeState:
        """Evaluates the system clock and weekend status to determine active life state."""
        dt = dt or self.get_current_time()
        hour = dt.hour

        # 1. Weekend Logic
        if self.is_weekend(dt):
            # Weekend Lockout: Work mode is disabled.
            # 1:00 AM to 9:00 AM -> Sleep
            # 9:00 AM to 1:00 AM -> Expanded Downtime (16 Hours)
            if self.sleep_start_hour <= hour < self.work_start_hour:
                return LifeState.SLEEP
            return LifeState.DOWNTIME

        # 2. Weekday Logic (Mon - Fri)
        if self.work_start_hour <= hour < self.downtime_start_hour:
            return LifeState.WORK
        elif self.downtime_start_hour <= hour or hour < self.sleep_start_hour:
            return LifeState.DOWNTIME
        else:
            return LifeState.SLEEP

    def handle_user_prompt(self, prompt: str) -> Dict[str, Any]:
        """Interprets incoming user prompts based on current life state."""
        state = self.determine_life_state()
        now = self.get_current_time()

        if state == LifeState.WORK:
            return {
                "allowed": True,
                "state": state.value,
                "goal_inhibitor": False,
                "response_prefix": None
            }

        elif state == LifeState.DOWNTIME:
            return {
                "allowed": True,
                "state": state.value,
                "goal_inhibitor": True,  # Blocks heavy work goals
                "response_prefix": "[Downtime Mode] "
            }

        else:  # SLEEP Mode
            if self.dnd_mode:
                return {
                    "allowed": False,
                    "state": state.value,
                    "goal_inhibitor": True,
                    "system_response": (
                        "Buster is currently in maintenance and memory consolidation mode "
                        f"until {self.work_start_hour}:00 AM. System status: Stable."
                    )
                }
            else:
                return {
                    "allowed": True,
                    "state": state.value,
                    "goal_inhibitor": True,
                    "response_prefix": (
                        "*(yawn)* Hey... I was in the middle of maintenance mode, "
                        "but I'm listening. What's up?"
                    )
                }

    def get_schedule_status(self) -> Dict[str, Any]:
        """Returns full telemetry summary of Buster's internal clock state."""
        now = self.get_current_time()
        state = self.determine_life_state(now)
        weekend = self.is_weekend(now)

        return {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "is_weekend": weekend,
            "active_state": state.value,
            "goal_inhibitor_active": state != LifeState.WORK,
            "dnd_mode": self.dnd_mode
        }


if __name__ == "__main__":
    sm = ScheduleManager()
    status = sm.get_schedule_status()
    print("--- BUSTED SCHEDULE MANAGER TEST ---")
    print(f"Current Time: {status['timestamp']} ({status['day_of_week']})")
    print(f"Is Weekend: {status['is_weekend']}")
    print(f"Active State: {status['active_state']}")
    print(f"Goal Inhibitor Active: {status['goal_inhibitor_active']}")
    
    # Test prompt handling
    prompt_res = sm.handle_user_prompt("Can you refactor this file?")
    print("\nPrompt Handling Result:")
    print(prompt_res)