from __future__ import annotations

from pathlib import Path
from typing import Any

from .sdk_agent import SDKAgent


class LifecycleSDKAgent(SDKAgent):
    agent_name = "lifecycle_agent"

    def __init__(self, sdk, root: str | Path = "."):
        super().__init__(sdk)
        self.root = Path(root).resolve()
        self._manager = None

    @property
    def manager(self):
        if self._manager is None:
            from buster.lifecycle.manager import LifecycleManager
            self._manager = LifecycleManager(self.root)
        return self._manager

    def run(self, task: Any = None):
        action = "status"

        if isinstance(task, str):
            action = task
        elif isinstance(task, dict):
            action = task.get("action", "status")

        if action == "health":
            result = self.manager.run_health()
            self.publish("lifecycle.health.updated", result)
            return result

        if action == "verify":
            result = self.manager.verify()
            self.publish("lifecycle.verified", result)
            return result

        if action == "backup":
            path = self.manager.backup()
            result = {"backup_path": path}
            self.publish("lifecycle.backup.created", result)
            return result

        if action == "plan":
            result = self.manager.plan()
            self.publish("lifecycle.plan.created", result)
            return result

        result = self.manager.status()
        self.publish("lifecycle.status.checked", result)
        return result
