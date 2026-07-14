from __future__ import annotations

from typing import Any
from .sdk_agent import SDKAgent


class OrchestratorAgent(SDKAgent):
    agent_name = "orchestrator_agent"

    def run(self, task: Any = None):
        orchestrator = self.sdk.require_service("agent_orchestrator")

        if isinstance(task, str):
            return orchestrator.run(task)

        if isinstance(task, dict):
            return orchestrator.run(task.get("request", ""))

        return {
            "status": "idle",
            "message": "Provide a request to orchestrate.",
        }
