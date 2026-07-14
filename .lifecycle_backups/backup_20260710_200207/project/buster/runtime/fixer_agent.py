from __future__ import annotations

from typing import Any, Dict

from .sdk_agent import SDKAgent


class FixerAgent(SDKAgent):
    agent_name = "fixer_agent"

    def run(self, task: Any = None) -> Dict[str, Any]:
        payload = task if isinstance(task, dict) else {"request": str(task or "")}

        result = {
            "agent": self.agent_name,
            "status": "safe_noop",
            "request": payload.get("request", ""),
            "summary": "Fixer Agent ran in safe mode and did not modify files.",
            "next_step": "Enable targeted patch mode when a concrete failing test or file issue is provided.",
        }

        self.publish("fixer.completed", result)
        return result
