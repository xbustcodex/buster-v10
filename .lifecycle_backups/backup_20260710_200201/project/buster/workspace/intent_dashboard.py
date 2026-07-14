from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.intent_os import MissionIntentRuntime


class IntentDashboard:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.runtime = MissionIntentRuntime(data_dir=data_dir)

    def snapshot(self) -> Dict[str, Any]:
        status = self.runtime.status()
        return {
            "title": "Intent & Activity Intelligence",
            "running": status["running"],
            "policy": status["policy"],
            "last_hypothesis": status["intent"]["last_hypothesis"],
            "signals": status["intent"]["signals"],
        }
