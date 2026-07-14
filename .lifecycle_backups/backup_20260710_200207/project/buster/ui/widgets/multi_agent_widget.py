from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from buster.workspace.multi_agent_dashboard import MultiAgentDashboard

class MultiAgentWidgetModel:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.dashboard = MultiAgentDashboard(data_dir=data_dir)

    def data(self) -> Dict[str, Any]:
        snap = self.dashboard.snapshot()
        return {"title": "Multi-Agent Collaboration", "status": "online" if snap["running"] else "ready", "timeline": snap["timeline"], "decisions": snap["decisions"], "messages": snap["messages"]}
