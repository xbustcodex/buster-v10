from __future__ import annotations

from datetime import datetime


class DailyRhythm:
    def greeting(self, name: str = "Adam", hour: int | None = None) -> str:
        hour = datetime.now().hour if hour is None else hour
        if hour < 12:
            return f"Good morning {name}."
        if hour < 18:
            return f"Good afternoon {name}."
        return f"Good evening {name}."

    def session_summary(self, tests: int = 0, passing: bool = True, next_goal: str = "continue development") -> str:
        status = "passing" if passing else "needs attention"
        return f"Current status: {tests} tests, {status}. Next goal: {next_goal}."
