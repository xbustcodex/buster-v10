from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from buster.runtime.storage import now


class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobManager:
    """
    Small synchronous job manager for v10.1.

    It gives Buster a common way to track long-running or multi-agent work.
    Later this can become threaded/async without changing the external API.
    """

    def __init__(self, sdk, registry=None):
        self.sdk = sdk
        self.registry = registry
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_handler(self, job_type: str, handler: Callable[[Dict[str, Any]], Any]):
        self.handlers[job_type] = handler

        self.sdk.publish(
            "job.handler.registered",
            {"job_type": job_type},
            source="job_manager",
        )

    def create_job(
        self,
        title: str,
        job_type: str = "generic",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        job_id = str(uuid4())

        job = {
            "job_id": job_id,
            "title": title,
            "type": job_type,
            "payload": payload or {},
            "status": JobStatus.PENDING,
            "result": None,
            "error": None,
            "created_at": now(),
            "updated_at": now(),
            "events": [],
        }

        self.jobs[job_id] = job

        if self.registry:
            self.registry.register_job(job_id, job)

        self.sdk.publish("job.created", job, source="job_manager")
        return job

    def update_job(self, job_id: str, status: str, result=None, error=None):
        job = self.require(job_id)
        job["status"] = status
        job["updated_at"] = now()

        if result is not None:
            job["result"] = result

        if error is not None:
            job["error"] = error

        item = {
            "status": status,
            "result": result,
            "error": error,
            "timestamp": now(),
        }
        job["events"].append(item)

        if self.registry:
            self.registry.update_job(job_id, job)

        self.sdk.publish(
            "job.updated",
            {
                "job_id": job_id,
                "status": status,
                "result": result,
                "error": error,
            },
            source="job_manager",
        )

        return job

    def run_job(self, job_id: str):
        job = self.require(job_id)
        self.update_job(job_id, JobStatus.RUNNING)

        handler = self.handlers.get(job["type"])

        try:
            if handler:
                result = handler(job)
            else:
                result = {
                    "message": "No handler registered. Job marked complete.",
                    "job_type": job["type"],
                }

            return self.update_job(job_id, JobStatus.COMPLETED, result=result)

        except Exception as exc:
            return self.update_job(job_id, JobStatus.FAILED, error=str(exc))

    def cancel_job(self, job_id: str):
        return self.update_job(job_id, JobStatus.CANCELLED)

    def require(self, job_id: str) -> Dict[str, Any]:
        if job_id not in self.jobs:
            raise KeyError(f"Unknown job: {job_id}")
        return self.jobs[job_id]

    def list_jobs(self) -> List[Dict[str, Any]]:
        return list(self.jobs.values())

    def status(self) -> Dict[str, Any]:
        counts = {}

        for job in self.jobs.values():
            counts[job["status"]] = counts.get(job["status"], 0) + 1

        return {
            "count": len(self.jobs),
            "counts": counts,
            "jobs": self.list_jobs()[-10:],
            "handlers": sorted(self.handlers.keys()),
        }
