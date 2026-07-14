from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from buster.multi_agent import MultiAgentCollaborationRuntime

class MultiAgentDashboard:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.runtime = MultiAgentCollaborationRuntime(data_dir=data_dir)

    def snapshot(self) -> Dict[str, Any]:
        status = self.runtime.status()
        return {"title": "Multi-Agent Collaboration", "running": status["running"], "timeline": status["blackboard"]["timeline"], "decisions": status["blackboard"]["decisions"], "messages": status["companion"]["messages"]}
