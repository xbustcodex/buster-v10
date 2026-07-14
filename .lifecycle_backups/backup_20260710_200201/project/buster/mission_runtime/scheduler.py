from __future__ import annotations

from typing import List

from .mission import Mission


class MissionScheduler:
    def __init__(self) -> None:
        self.queue: List[Mission] = []
        self.completed: List[Mission] = []

    def submit(self, mission: Mission) -> Mission:
        self.queue.append(mission)
        return mission

    def next(self) -> Mission | None:
        if not self.queue:
            return None
        return self.queue.pop(0)

    def mark_completed(self, mission: Mission) -> None:
        self.completed.append(mission)

    def status(self) -> dict:
        return {
            "queued": len(self.queue),
            "completed": len(self.completed),
            "queue": [m.to_dict() for m in self.queue],
            "completed_missions": [m.to_dict() for m in self.completed[-10:]],
        }
