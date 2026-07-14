import itertools
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any

@dataclass
class ScheduledTask:
    id: int
    title: str
    description: str
    status: str = "queued"
    result: str = ""
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    started_at: str = ""
    finished_at: str = ""

class TaskScheduler:
    def __init__(self, thread_pool):
        self.thread_pool = thread_pool
        self._ids = itertools.count(1)
        self.tasks = {}
        self.lock = threading.Lock()

    def submit(self, title: str, description: str, fn: Callable[..., Any], *args, **kwargs):
        task = ScheduledTask(next(self._ids), title, description)
        with self.lock:
            self.tasks[task.id] = task

        def runner():
            task.status = "running"
            task.started_at = datetime.now().isoformat(timespec="seconds")
            try:
                task.result = str(fn(*args, **kwargs))
                task.status = "done"
            except Exception as exc:
                task.error = str(exc)
                task.status = "failed"
            task.finished_at = datetime.now().isoformat(timespec="seconds")
            return task.result or task.error

        self.thread_pool.submit(runner)
        return task

    def list_tasks(self):
        with self.lock:
            items = list(self.tasks.values())[-20:]
        if not items:
            return "No tasks yet."
        return "\n".join([f"#{t.id} {t.status.upper()} - {t.title}" for t in items])

    def status(self, task_id=None):
        with self.lock:
            items = list(self.tasks.values())[-5:] if task_id is None else ([self.tasks[task_id]] if task_id in self.tasks else [])
        if not items:
            return "No matching task."
        lines = []
        for t in items:
            lines += [f"Task #{t.id}: {t.title}", f"Status: {t.status}", f"Created: {t.created_at}"]
            if t.started_at: lines.append(f"Started: {t.started_at}")
            if t.finished_at: lines.append(f"Finished: {t.finished_at}")
            if t.result: lines.append("Result: " + t.result[:1200])
            if t.error: lines.append("Error: " + t.error[:1200])
            lines.append("")
        return "\n".join(lines).strip()

    def summary(self):
        with self.lock:
            vals = list(self.tasks.values())
        return f"Tasks total={len(vals)}, running={sum(t.status=='running' for t in vals)}, queued={sum(t.status=='queued' for t in vals)}, done={sum(t.status=='done' for t in vals)}, failed={sum(t.status=='failed' for t in vals)}"
