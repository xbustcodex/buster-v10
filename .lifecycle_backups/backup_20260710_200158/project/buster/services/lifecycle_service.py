import json
from pathlib import Path

from buster.lifecycle.manager import LifecycleManager


class LifecycleService:
    def __init__(self, root=None):
        self.root = Path(root or Path.cwd()).resolve()
        self.manager = LifecycleManager(self.root)

    def status(self):
        return self.manager.status()

    def health(self):
        return self.manager.run_health()

    def verify(self):
        return self.manager.verify()

    def plan(self):
        return self.manager.plan()

    def backup(self):
        return {"backup_path": self.manager.backup()}

    def rollback(self):
        return {"success": self.manager.rollback()}

    def snapshot(self):
        status = self.status()
        health = self.health()
        verify = self.verify()
        plan = self.plan()

        return {
            "status": status,
            "health": health,
            "verify": verify,
            "plan": plan,
        }
