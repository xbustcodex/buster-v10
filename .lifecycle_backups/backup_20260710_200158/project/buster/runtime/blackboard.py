from __future__ import annotations

from typing import Any, Dict, List
from buster.runtime.storage import now


class RuntimeBlackboard:
    def __init__(self, sdk):
        self.sdk = sdk
        self.data: Dict[str, Any] = {
            "goal": None,
            "workspace": {},
            "problems": [],
            "decisions": [],
            "artifacts": [],
            "notes": [],
            "updated_at": now(),
        }

    def set_goal(self, goal: str):
        self.data["goal"] = goal
        self.data["updated_at"] = now()
        self.sdk.publish("blackboard.goal.updated", {"goal": goal}, source="blackboard")
        return self.snapshot()

    def write(self, key: str, value: Any, source: str = "blackboard"):
        self.data[key] = value
        self.data["updated_at"] = now()
        self.sdk.publish("blackboard.updated", {"key": key, "value": value}, source=source)
        return value

    def append(self, key: str, value: Any, source: str = "blackboard"):
        self.data.setdefault(key, [])
        if not isinstance(self.data[key], list):
            self.data[key] = [self.data[key]]
        self.data[key].append(value)
        self.data["updated_at"] = now()
        self.sdk.publish("blackboard.appended", {"key": key, "value": value}, source=source)
        return value

    def read(self, key: str, default=None):
        return self.data.get(key, default)

    def snapshot(self):
        return dict(self.data)
