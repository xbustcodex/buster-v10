from __future__ import annotations

from typing import Any, Dict, List


class AgentOrchestrator:
    def __init__(self, sdk, agents, jobs, registry, blackboard, memory):
        self.sdk = sdk
        self.agents = agents
        self.jobs = jobs
        self.registry = registry
        self.blackboard = blackboard
        self.memory = memory

    def choose_agents(self, request: str) -> List[str]:
        text = request.lower()
        selected = ["planner"]

        if "build" in text or "create" in text or "feature" in text:
            selected.append("builder")

        if "test" in text or "validate" in text or "pytest" in text:
            selected.append("tester")

        if "review" in text or "quality" in text or "architecture" in text:
            selected.append("reviewer")

        if "fix" in text or "error" in text or "failed" in text:
            selected.append("fixer")

        if "health" in text or "lifecycle" in text:
            selected.append("lifecycle")

        return list(dict.fromkeys(selected))

    def run(self, request: str) -> Dict[str, Any]:
        self.blackboard.set_goal(request)

        selected_agents = self.choose_agents(request)

        self.sdk.publish(
            "orchestrator.started",
            {"request": request, "agents": selected_agents},
            source="agent_orchestrator",
        )

        plan = self.agents.run("planner", {"request": request})
        self.memory.record("planner", "plan", {"status": "completed", "plan": plan})

        self.blackboard.write("plan", plan, source="agent_orchestrator")

        results = []

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

            results.append(completed)
            self.blackboard.append("artifacts", completed, source="agent_orchestrator")

            result_payload = completed.get("result") or {}
            agent_name = step.get("agent", "unknown")
            self.memory.record(agent_name, step.get("job_type", "job"), result_payload)

            if result_payload.get("status") in {"failed", "error"}:
                self.blackboard.append("problems", result_payload, source="agent_orchestrator")
                break

        final_status = "completed"
        for item in results:
            payload = item.get("result") or {}
            if payload.get("status") in {"failed", "error"}:
                final_status = "failed"
                break

        output = {
            "request": request,
            "selected_agents": selected_agents,
            "plan": plan,
            "jobs": results,
            "status": final_status,
            "blackboard": self.blackboard.snapshot(),
            "agent_memory": self.memory.status(),
        }

        self.sdk.publish(
            "orchestrator.finished",
            {"request": request, "status": final_status, "jobs": len(results)},
            source="agent_orchestrator",
        )

        return output
