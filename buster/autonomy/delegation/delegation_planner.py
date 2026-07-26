from __future__ import annotations

import json
import uuid
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from buster.telemetry.trace_context import TraceContext
from buster.telemetry.telemetry_service import TelemetryService
from buster.autonomy.delegation.worker_pool import WorkerPoolManager
from buster.autonomy.delegation.capability_matrix import AgentCapabilityMatrix, WorkerRole


class DelegationPlanner:
    """Orchestrates parent-child task lineage, worker dispatching, cancellation, and DLQ persistence."""

    def __init__(
        self,
        worker_pool: WorkerPoolManager,
        telemetry: TelemetryService,
        dlq_path: str = "data/dead_letter_queue.jsonl",
    ):
        self._lock = threading.RLock()
        self.worker_pool = worker_pool
        self.telemetry = telemetry
        self.dlq_file = Path(dlq_path)
        self.dlq_file.parent.mkdir(parents=True, exist_ok=True)

        self.tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> task dict
        self.children: Dict[str, List[str]] = {}   # parent_id -> list of child_ids

    def create_subtask(
        self,
        parent_task_id: str,
        title: str,
        required_capabilities: List[str],
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Spawns a child task linked to a parent task in trace context."""
        with self._lock:
            subtask_id = f"sub_{uuid.uuid4().hex[:8]}"
            role = AgentCapabilityMatrix.resolve_role_for_task(required_capabilities)

            task_record = {
                "task_id": subtask_id,
                "parent_task_id": parent_task_id,
                "title": title,
                "role": role.value if role else WorkerRole.BUILDER.value,
                "required_capabilities": required_capabilities,
                "payload": payload or {},
                "status": "pending",  # pending, running, completed, failed, cancelled
            }

            self.tasks[subtask_id] = task_record
            self.children.setdefault(parent_task_id, []).append(subtask_id)

            self.telemetry.logger.log_event(
                event_type="task.delegated",
                component="delegation_planner",
                status="info",
                extra={"task_id": subtask_id, "parent_task_id": parent_task_id, "role": task_record["role"]},
            )

            return task_record

    def cancel_task_tree(self, parent_task_id: str) -> List[str]:
        """Recursively cancels a parent task and all of its descendant child subtasks."""
        cancelled_ids = []

        with self._lock:
            def _cancel_node(tid: str):
                if tid in self.tasks and self.tasks[tid]["status"] not in {"completed", "cancelled"}:
                    self.tasks[tid]["status"] = "cancelled"
                    cancelled_ids.append(tid)

                    self.telemetry.logger.log_event(
                        event_type="task.cancelled",
                        component="delegation_planner",
                        status="warning",
                        extra={"task_id": tid},
                    )

                for child_id in self.children.get(tid, []):
                    _cancel_node(child_id)

            _cancel_node(parent_task_id)

        return cancelled_ids

    def send_to_dlq(self, task_id: str, error_reason: str, diagnostic: Optional[Dict[str, Any]] = None) -> None:
        """Parks an unrecoverable or failed task into the Dead-Letter Queue (DLQ)."""
        with self._lock:
            task_data = self.tasks.get(task_id, {"task_id": task_id})
            task_data["status"] = "failed"

            dlq_record = {
                "task_id": task_id,
                "task_data": task_data,
                "error_reason": error_reason,
                "diagnostic": diagnostic,
                "dlq_timestamp": self.telemetry.logger.log_event(
                    event_type="task.blocked",
                    component="dead_letter_queue",
                    status="failed",
                    extra={"task_id": task_id, "reason": error_reason},
                )["timestamp"],
            }

            line = json.dumps(dlq_record) + "\n"
            with open(self.dlq_file, "a", encoding="utf-8") as f:
                f.write(line)