# buster/node/task_bridge.py
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskPayload:
    task_id: str
    command: str
    target_node: str
    sender_node: str
    status: str = "pending"  # pending, running, completed, failed
    output: str = ""
    timestamp: str = ""


class WebSocketTaskBridge:
    """Async task bridge protocol for streaming execution across distributed nodes."""

    def __init__(self, node_id: str = "desktop_host") -> None:
        self.node_id = node_id
        self.active_tasks: Dict[str, TaskPayload] = {}
        self.subscribers: List[Callable[[TaskPayload], None]] = []

    def create_task(self, task_id: str, command: str, target_node: str) -> TaskPayload:
        """Creates and registers a new cross-node execution task."""
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        task = TaskPayload(
            task_id=task_id,
            command=command,
            target_node=target_node,
            sender_node=self.node_id,
            status="pending",
            timestamp=now_iso,
        )
        self.active_tasks[task_id] = task
        logger.info(f"Task created [{task_id}] targeting node [{target_node}]")
        return task

    async def execute_task_stream(self, task_id: str, mock_output_chunks: List[str]) -> TaskPayload:
        """Simulates async streaming execution of terminal output across nodes."""
        if task_id not in self.active_tasks:
            raise ValueError(f"Task {task_id} not found.")

        task = self.active_tasks[task_id]
        task.status = "running"
        accumulated_output = []

        for chunk in mock_output_chunks:
            await asyncio.sleep(0.01)  # Simulate network / process stream latency
            accumulated_output.append(chunk)
            task.output = "\n".join(accumulated_output)
            self._notify_subscribers(task)

        task.status = "completed"
        self._notify_subscribers(task)
        return task

    def subscribe(self, callback: Callable[[TaskPayload], None]) -> None:
        """Subscribes to real-time task status and output stream events."""
        self.subscribers.append(callback)

    def _notify_subscribers(self, task: TaskPayload) -> None:
        for cb in self.subscribers:
            try:
                cb(task)
            except Exception as e:
                logger.error(f"Error in task bridge subscriber callback: {e}")