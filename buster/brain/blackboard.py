from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional


class SharedBlackboard:
    """Thread-safe central memory hub for worker coordination & task tree status."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.storage_path = storage_path if storage_path else os.path.join(base_dir, "blackboard_state.json")
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        with self._lock:
            if not os.path.exists(self.storage_path):
                initial_state = {
                    "active_goal": None,
                    "delegation_tree": [],
                    "active_leases": {},
                    "system_status": "Idle",
                    "updated_at": datetime.now().isoformat()
                }
                self._write_state_unlocked(initial_state)

    def _read_state_unlocked(self) -> Dict[str, Any]:
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"active_goal": None, "delegation_tree": [], "active_leases": {}, "system_status": "Idle"}

    def _write_state_unlocked(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = datetime.now().isoformat()
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def set_goal(self, goal_title: str) -> None:
        with self._lock:
            state = self._read_state_unlocked()
            state["active_goal"] = goal_title
            state["delegation_tree"] = []
            state["system_status"] = "Delegating"
            self._write_state_unlocked(state)

    def update_delegation_tree(self, tasks: List[Dict[str, Any]]) -> None:
        with self._lock:
            state = self._read_state_unlocked()
            state["delegation_tree"] = tasks
            self._write_state_unlocked(state)

    def assign_worker_lease(self, worker_id: str, task_id: str, task_name: str) -> None:
        with self._lock:
            state = self._read_state_unlocked()
            state["active_leases"][worker_id] = {
                "task_id": task_id,
                "task_name": task_name,
                "leased_at": datetime.now().isoformat(),
                "status": "Running"
            }
            self._write_state_unlocked(state)

    def release_worker_lease(self, worker_id: str) -> None:
        with self._lock:
            state = self._read_state_unlocked()
            if worker_id in state["active_leases"]:
                del state["active_leases"][worker_id]
            self._write_state_unlocked(state)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return self._read_state_unlocked()