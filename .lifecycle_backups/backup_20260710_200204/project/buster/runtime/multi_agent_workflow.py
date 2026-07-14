from __future__ import annotations

from typing import Any, Dict, List


class MultiAgentWorkflowRunner:
    def __init__(self, sdk, agents, jobs):
        self.sdk = sdk
        self.agents = agents
        self.jobs = jobs

    def run_request(self, request: str) -> Dict[str, Any]:
        plan = self.agents.run("planner", {"request": request})

        workflow = {
            "request": request,
            "plan": plan,
            "jobs": [],
            "status": "running",
        }

        self.sdk.publish("workflow.started", {
            "request": request,
            "steps": plan.get("step_count", 0),
        }, source="workflow_runner")

        for step in plan.get("steps", []):
            job = self.agents.run("jobs", {
                "action": "create",
                "title": step["title"],
                "job_type": step["job_type"],
                "payload": step.get("payload", {}),
            })

            completed = self.agents.run("jobs", {
                "action": "run",
                "job_id": job["job_id"],
            })

            workflow["jobs"].append(completed)

            if completed.get("status") == "failed":
                workflow["status"] = "failed"
                break

        if workflow["status"] != "failed":
            workflow["status"] = "completed"

        self.sdk.publish("workflow.finished", {
            "request": request,
            "status": workflow["status"],
            "jobs": len(workflow["jobs"]),
        }, source="workflow_runner")

        return workflow
