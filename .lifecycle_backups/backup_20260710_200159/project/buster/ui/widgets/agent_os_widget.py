from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.workspace.agent_os_dashboard import AgentOSDashboard


class AgentOSWidgetModel:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.dashboard = AgentOSDashboard(data_dir=data_dir)

    def data(self) -> Dict[str, Any]:
        snap = self.dashboard.snapshot()
        return {
            "title": "Agent Runtime & Living Companion",
            "status": "online",
            "agent_count": len(snap["agents"]),
            "messages": snap["messages"],
            "timeline": snap["timeline"],
        }
