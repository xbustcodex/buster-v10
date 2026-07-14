from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.agent_os import LivingCompanionRuntime


class AgentOSDashboard:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.runtime = LivingCompanionRuntime(data_dir=data_dir)

    def snapshot(self) -> Dict[str, Any]:
        status = self.runtime.status()
        return {
            "title": "Agent OS",
            "companion_running": status["running"],
            "messages": status["messages"],
            "agents": status["agents"]["agents"],
            "timeline": status["agents"]["timeline"],
        }
