from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.workspace_awareness import WorkspaceAwarenessRuntime


class WorkspaceAwarenessDashboard:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.runtime = WorkspaceAwarenessRuntime(data_dir=data_dir)

    def snapshot(self) -> Dict[str, Any]:
        status = self.runtime.status()
        return {
            "title": "Continuous Workspace Awareness",
            "running": status["running"],
            "event_count": status["event_count"],
            "recent_events": status["events"],
            "companion_messages": status["companion"]["messages"],
        }
