"""
Buster Kernel - Async Priority Task Scheduler
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
import uuid


class TaskPriority(Enum):
    LOW = 30
    NORMAL = 20
    HIGH = 10
    CRITICAL = 0


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass(order=True)
class KernelTask:
    priority: int
    task_id: str = field(compare=False)
    name: str = field(compare=False)
    agent_id: str = field(compare=False)
    coro_func: Callable[..., Any] = field(compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    result: Optional[Any] = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)


class TaskScheduler:
    """Async priority task runner for agent execution streams."""

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[KernelTask] = asyncio.PriorityQueue()
        self._tasks: Dict[str, KernelTask] = {}
        self._worker_task: Optional[asyncio.Task] = None

    def schedule(
        self,
        name: str,
        agent_id: str,
        coro_func: Callable[..., Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        task_id = f"TSK-{uuid.uuid4().hex[:6]}"
        task = KernelTask(
            priority=priority.value,
            task_id=task_id,
            name=name,
            agent_id=agent_id,
            coro_func=coro_func,
        )
        self._tasks[task_id] = task
        self._queue.put_nowait(task)
        return task_id

    async def start(self) -> None:
        """Starts the async task processing loop."""
        self._worker_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self) -> None:
        while True:
            task = await self._queue.get()
            task.status = TaskStatus.RUNNING
            try:
                task.result = await task.coro_func()
                task.status = TaskStatus.COMPLETED
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
            finally:
                self._queue.task_done()