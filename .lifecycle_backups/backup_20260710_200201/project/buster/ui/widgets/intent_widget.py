from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.workspace.intent_dashboard import IntentDashboard


class IntentWidgetModel:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.dashboard = IntentDashboard(data_dir=data_dir)

    def data(self) -> Dict[str, Any]:
        snap = self.dashboard.snapshot()
        return {
            "title": "Intent Intelligence",
            "status": "online" if snap["running"] else "ready",
            "policy": snap["policy"],
            "last_hypothesis": snap["last_hypothesis"],
            "signals": snap["signals"],
        }
