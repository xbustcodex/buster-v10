from __future__ import annotations

from typing import Any

from .sdk_agent import SDKAgent


class RegistryAgent(SDKAgent):
    agent_name = "registry_agent"

    def run(self, task: Any = None):
        registry = self.sdk.require_service("runtime_registry")

        if task is None or task == "status":
            return registry.status()

        if isinstance(task, dict):
            action = task.get("action", "status")

            if action == "capability":
                return {
                    "capability": task.get("capability"),
                    "services": registry.services_for_capability(task.get("capability")),
                }

        return registry.status()
