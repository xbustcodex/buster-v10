from __future__ import annotations

import time
import signal
import sys
from typing import Dict, Any, List, Optional
from buster.brain.blackboard import SharedBlackboard
from buster.brain.dlq_manager import DLQManager
from buster.brain.task_state_manager import TaskStateManager


class TaskDelegator:
    """Technician Mindset: Decomposes goals into sub-tasks and manages execution & state persistence."""

    def __init__(
        self, 
        blackboard: Optional[SharedBlackboard] = None,
        dlq_manager: Optional[DLQManager] = None,
        state_manager: Optional[TaskStateManager] = None
    ) -> None:
        self.blackboard = blackboard if blackboard else SharedBlackboard()
        self.dlq = dlq_manager if dlq_manager else DLQManager()
        self.state_manager = state_manager if state_manager else TaskStateManager()

        # Hook signal handlers so shutting down PC or stopping terminal commits state safely
        signal.signal(signal.SIGINT, self._handle_graceful_shutdown)
        signal.signal(signal.SIGTERM, self._handle_graceful_shutdown)

        # Reload any saved state on boot
        self._restore_persisted_state()

    def _restore_persisted_state(self) -> None:
        """Restores pending tasks and active state from task_state.json if present on startup."""
        state = self.state_manager.load_state()
        saved_tree = state.get("delegation_tree", [])
        saved_goal = state.get("goal", "")

        if saved_tree:
            print(f"[Task Delegator] Restored {len(saved_tree)} unfinished tasks from disk for goal: '{saved_goal}'")
            if saved_goal:
                self.blackboard.set_goal(saved_goal)
            self.blackboard.update_delegation_tree(saved_tree)

    def _persist_current_state(self) -> None:
        """Helper to checkpoint current active blackboard state to disk."""
        snapshot = self.blackboard.get_snapshot()
        self.state_manager.save_state(
            goal=snapshot.get("goal", ""),
            delegation_tree=snapshot.get("delegation_tree", []),
            active_leases=snapshot.get("active_leases", {})
        )

    def decompose_and_delegate(self, goal: str) -> Dict[str, Any]:
        """Parses a user goal into structured sub-tasks, updates the Blackboard, and persists to disk."""
        print(f"[Task Delegator] Decomposing goal: '{goal}'")
        self.blackboard.set_goal(goal)

        subtasks = [
            {
                "id": "task-1",
                "title": f"Analyze context for: {goal}",
                "status": "Queued",
                "worker": "Worker-1",
                "circuit": "api_gateway"
            },
            {
                "id": "task-2",
                "title": "Build unit test framework patch",
                "status": "Queued",
                "worker": "Worker-2",
                "circuit": "code_executor"
            },
            {
                "id": "task-3",
                "title": "Verify execution & record metrics",
                "status": "Pending",
                "worker": "Worker-3",
                "circuit": "file_system"
            }
        ]

        self.blackboard.update_delegation_tree(subtasks)
        self._persist_current_state()

        return {"goal": goal, "subtask_count": len(subtasks), "tasks": subtasks}

    def execute_worker_task(self, task_id: str, worker_id: str, simulate_failure: bool = False) -> None:
        """Executes a worker task, acquires leases, updates task state, and saves queue snapshot."""
        snapshot = self.blackboard.get_snapshot()
        tree = snapshot.get("delegation_tree", [])
        
        target_task = next((t for t in tree if t["id"] == task_id), None)
        task_name = target_task["title"] if target_task else "General Subtask"
        circuit_name = target_task.get("circuit", "code_executor") if target_task else "code_executor"

        print(f"[*] [{worker_id}] Acquiring lease for [{task_id}]: {task_name}")
        self.blackboard.assign_worker_lease(worker_id, task_id, task_name)
        
        # Mark task as In Progress and write state
        if target_task:
            target_task["status"] = "In Progress"
            self.blackboard.update_delegation_tree(tree)
        self._persist_current_state()

        time.sleep(0.2)  # Fast execution for verification

        if simulate_failure:
            print(f"[X] [{worker_id}] Task [{task_id}] failed! Logging to DLQ...")
            if target_task:
                target_task["status"] = "Failed"
            self.dlq.record_failure(
                task_id=task_id,
                task_name=task_name,
                circuit_name=circuit_name,
                error_msg="RuntimeExecutionError: Worker process encountered an unexpected failure."
            )
        else:
            print(f"[+] [{worker_id}] Completed [{task_id}]. Releasing lease...")
            if target_task:
                target_task["status"] = "Completed"
            self.dlq.record_success(circuit_name=circuit_name)

        self.blackboard.release_worker_lease(worker_id)
        self.blackboard.update_delegation_tree(tree)

        # Update disk state after task status change
        self._persist_current_state()

    def _handle_graceful_shutdown(self, signum: int, frame: Any) -> None:
        """Saves all active states immediately before terminal process terminates."""
        print("\n[Task Delegator] System interrupt detected! Flushing state to disk before shutdown...")
        self._persist_current_state()
        sys.exit(0)


if __name__ == "__main__":
    delegator = TaskDelegator()
    result = delegator.decompose_and_delegate("Refactor v17 Core Engine")
    print("Delegation Plan Created & Checkpointed:")
    print(result)
    delegator.execute_worker_task("task-1", "Worker-1", simulate_failure=False)