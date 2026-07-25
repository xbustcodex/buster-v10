from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict


class GoalStorage:
    """Thread-safe JSON file persistence engine for goals mapping dicts."""

    def __init__(self, storage_path: str | Path = "data/goals_registry.json"):
        self.storage_path = Path(storage_path)
        self._lock = threading.RLock()
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        with self._lock:
            if not self.storage_path.parent.exists():
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.storage_path.exists():
                self._write_raw({})

    def _write_raw(self, data: Dict[str, Any]) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_all(self) -> Dict[str, Any]:
        with self._lock:
            if not self.storage_path.exists():
                return {}
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}

    def get_goal(self, goal_id: str) -> Dict[str, Any] | None:
        with self._lock:
            data = self.load_all()
            return data.get(goal_id)

    def save_goal(self, goal_data: Dict[str, Any]) -> None:
        with self._lock:
            data = self.load_all()
            data[goal_data["id"]] = goal_data
            self._write_raw(data)

    def save_all(self, goals_map: Dict[str, Any]) -> None:
        with self._lock:
            self._write_raw(goals_map)