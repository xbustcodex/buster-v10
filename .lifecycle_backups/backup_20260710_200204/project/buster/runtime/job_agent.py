from __future__ import annotations

from typing import Any

from .sdk_agent import SDKAgent


class JobAgent(SDKAgent):
    agent_name = "job_agent"

    def run(self, task: Any = None):
        job_manager = self.sdk.require_service("job_manager")

        if task is None:
            return job_manager.status()

        if isinstance(task, str):
            if task == "status":
                return job_manager.status()
            raise ValueError(f"Unknown job task: {task}")

        action = task.get("action", "status")

        if action == "create":
            return job_manager.create_job(
                title=task.get("title", "Untitled Job"),
                job_type=task.get("job_type", "generic"),
                payload=task.get("payload", {}),
            )

        if action == "run":
            return job_manager.run_job(task["job_id"])

        if action == "cancel":
            return job_manager.cancel_job(task["job_id"])

        if action == "list":
            return job_manager.list_jobs()

        return job_manager.status()
