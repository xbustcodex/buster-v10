from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional


class DLQManager:
    """Thread-safe manager for failed tasks (Dead-Letter Queue) & circuit states."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.storage_path = storage_path if storage_path else os.path.join(base_dir, "dlq_state.json")
        self._lock = threading.RLock()  # Use RLock to prevent self-deadlock
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        with self._lock:
            if not os.path.exists(self.storage_path):
                initial_state = {
                    "dlq_items": [],
                    "circuits": {
                        "api_gateway": {"status": "CLOSED", "failure_count": 0},
                        "code_executor": {"status": "CLOSED", "failure_count": 0},
                        "file_system": {"status": "CLOSED", "failure_count": 0}
                    },
                    "metrics": {
                        "completed_tasks": 0,
                        "failed_tasks": 0,
                        "circuit_trips": 0
                    }
                }
                self._write_state(initial_state)

    def _read_state(self) -> Dict[str, Any]:
        with self._lock:
            if not os.path.exists(self.storage_path):
                return {"dlq_items": [], "circuits": {}, "metrics": {"completed_tasks": 0, "failed_tasks": 0, "circuit_trips": 0}}
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {"dlq_items": [], "circuits": {}, "metrics": {"completed_tasks": 0, "failed_tasks": 0, "circuit_trips": 0}}

    def _write_state(self, state: Dict[str, Any]) -> None:
        with self._lock:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

    def record_failure(self, task_id: str, task_name: str, circuit_name: str, error_msg: str) -> None:
        """Pushes a task into DLQ, updates metrics, and trips circuit if threshold exceeded."""
        with self._lock:
            state = self._read_state()
            
            # 1. Add to DLQ
            dlq_entry = {
                "id": task_id,
                "name": task_name,
                "circuit": circuit_name,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            state["dlq_items"].append(dlq_entry)
            state["metrics"]["failed_tasks"] += 1

            # 2. Update Circuit Breaker
            circuit = state["circuits"].get(circuit_name, {"status": "CLOSED", "failure_count": 0})
            circuit["failure_count"] += 1
            
            if circuit["failure_count"] >= 3:
                circuit["status"] = "OPEN (TRIPPED)"
                state["metrics"]["circuit_trips"] += 1

            state["circuits"][circuit_name] = circuit
            self._write_state(state)
            print(f"[!] [DLQ] Recorded failure for '{task_name}' on circuit '{circuit_name}'")

    def record_success(self, circuit_name: Optional[str] = None) -> None:
        """Increments success counter and clears circuit failure count if closed."""
        with self._lock:
            state = self._read_state()
            state["metrics"]["completed_tasks"] += 1
            
            if circuit_name and circuit_name in state["circuits"]:
                if state["circuits"][circuit_name]["status"] == "CLOSED":
                    state["circuits"][circuit_name]["failure_count"] = 0

            self._write_state(state)

    def reset_circuit(self, circuit_name: str) -> None:
        """Resets a tripped circuit breaker back to CLOSED status."""
        with self._lock:
            state = self._read_state()
            if circuit_name in state["circuits"]:
                state["circuits"][circuit_name] = {"status": "CLOSED", "failure_count": 0}
                self._write_state(state)
                print(f"[+] [Circuit Breaker] Reset '{circuit_name}' to CLOSED.")

    def dismiss_dlq_item(self, task_id: str) -> None:
        """Removes a resolved/dismissed item from the DLQ."""
        with self._lock:
            state = self._read_state()
            state["dlq_items"] = [item for item in state["dlq_items"] if item["id"] != task_id]
            self._write_state(state)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return self._read_state()


if __name__ == "__main__":
    dlq = DLQManager()
    
    # Fast test trigger
    for i in range(1, 4):
        dlq.record_failure(
            task_id=f"fail-{i}",
            task_name=f"Execute core module patch {i}",
            circuit_name="code_executor",
            error_msg="SyntaxError: unexpected EOF while parsing"
        )
    print("[+] DLQ and Circuit Breaker test finished cleanly!")