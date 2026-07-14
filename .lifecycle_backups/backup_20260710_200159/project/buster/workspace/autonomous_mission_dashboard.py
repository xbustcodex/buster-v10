from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.mission_runtime import AutonomousMissionRuntime


class AutonomousMissionDashboard:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.runtime = AutonomousMissionRuntime(data_dir=data_dir)

    def snapshot(self) -> Dict[str, Any]:
        status = self.runtime.status()
        return {
            "title": "Autonomous Mission Runtime",
            "running": status["running"],
            "queued": status["scheduler"]["queued"],
            "completed": status["scheduler"]["completed"],
            "capabilities": status["capabilities"],
            "messages": status["companion"]["messages"],
        }
