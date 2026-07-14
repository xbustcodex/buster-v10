from __future__ import annotations

import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Callable, Any, Optional


@dataclass
class Job:
    id: str
    title: str
    status: str = "queued"
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


class JobQueue:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, title: str, fn: Callable[[], Any]) -> Job:
        job = Job(id=str(uuid.uuid4())[:8], title=title)

        with self._lock:
            self.jobs[job.id] = job

        thread = threading.Thread(
            target=self._run,
            args=(job.id, fn),
            daemon=True,
        )
        thread.start()
        return job

    def _run(self, job_id: str, fn: Callable[[], Any]):
        job = self.jobs[job_id]
        job.status = "running"
        job.started_at = time.time()

        try:
            job.result = fn()
            job.status = "finished"
        except Exception as e:
            job.error = str(e)
            job.status = "failed"
        finally:
            job.finished_at = time.time()

    def list_jobs(self):
        with self._lock:
            return list(self.jobs.values())

    def get(self, job_id: str):
        return self.jobs.get(job_id)
