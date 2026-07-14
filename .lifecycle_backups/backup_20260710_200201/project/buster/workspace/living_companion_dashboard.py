from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.living_companion import LivingAICompanionRuntime


class LivingCompanionDashboard:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.runtime = LivingAICompanionRuntime(data_dir=data_dir)

    def snapshot(self) -> Dict[str, Any]:
        status = self.runtime.status()
        return {
            "title": "Buster v7 Living AI Companion",
            "running": status["running"],
            "mode": status["mode"],
            "spoken": status["voice"]["spoken"],
            "queued": status["voice"]["queued"],
            "skills": status["skills"]["skills"],
        }
