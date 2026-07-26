from __future__ import annotations

import json
import os
import threading
from typing import Dict, Any, List, Optional


class TaskStateManager:
    """Manages disk persistence and state recovery for Buster's active tasks and leases."""

    def __init__(self, state_file_path: Optional[str] = None):
        if state_file_path:
            self.state_file_path = state_file_path
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.state_file_path = os.path.join(base_dir, "task_state.json")

        self._lock = threading.Lock()

    def save_state(self, goal: str, delegation_tree: List[Dict[str, Any]], active_leases: Dict[str, Any]) -> bool:
        """Atomically saves the current active queue and worker state to disk."""
        with self._lock:
            payload = {
                "goal": goal,
                "delegation_tree": delegation_tree,
                "active_leases": active_leases,
                "version": "v10"
            }
            try:
                temp_path = f"{self.state_file_path}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                os.replace(temp_path, self.state_file_path)
                return True
            except Exception as e:
                print(f"[TaskStateManager] Failed to save state: {e}")
                return False

    def load_state(self) -> Dict[str, Any]:
        """Loads saved task state from disk upon boot."""
        with self._lock:
            if not os.path.exists(self.state_file_path):
                return {"goal": "", "delegation_tree": [], "active_leases": {}}

            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[TaskStateManager] Failed to read state file: {e}")
                return {"goal": "", "delegation_tree": [], "active_leases": {}}

    def clear_state(self) -> None:
        """Clears state file when all queue items complete cleanly."""
        with self._lock:
            if os.path.exists(self.state_file_path):
                try:
                    os.remove(self.state_file_path)
                except Exception:
                    pass