from __future__ import annotations

from typing import Any, Dict


class SDKAgent:
    agent_name = "sdk_agent"

    def __init__(self, sdk):
        self.sdk = sdk

    def publish(self, event_type: str, payload=None):
        return self.sdk.publish(event_type, payload or {}, source=self.agent_name)

    def status(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "status": "ready",
        }

    def run(self, task: Any = None):
        return self.status()
