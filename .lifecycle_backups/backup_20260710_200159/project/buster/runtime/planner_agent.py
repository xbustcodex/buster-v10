from __future__ import annotations

from typing import Any, Dict, List

from .sdk_agent import SDKAgent


class PlannerAgent(SDKAgent):
    agent_name = "planner_agent"

    def run(self, task: Any = None):
        request = ""

        if isinstance(task, str):
            request = task
        elif isinstance(task, dict):
            request = task.get("request", "")

        request_lower = request.lower()

        steps: List[Dict[str, Any]] = []

        if "test" in request_lower or "pytest" in request_lower:
            steps.append({
                "title": "Run project tests",
                "job_type": "agent.test",
                "agent": "tester",
                "payload": {"request": request},
            })

        elif "review" in request_lower:
            steps.append({
                "title": "Review project code",
                "job_type": "agent.review",
                "agent": "reviewer",
                "payload": {"request": request},
            })

        elif "fix" in request_lower:
            steps.extend([
                {
                    "title": "Review issue before fix",
                    "job_type": "agent.review",
                    "agent": "reviewer",
                    "payload": {"request": request},
                },
                {
                    "title": "Apply safe fix recommendation",
                    "job_type": "agent.fix",
                    "agent": "fixer",
                    "payload": {"request": request},
                },
                {
                    "title": "Run tests after fix",
                    "job_type": "agent.test",
                    "agent": "tester",
                    "payload": {"request": request},
                },
            ])

        else:
            steps.extend([
                {
                    "title": "Plan build task",
                    "job_type": "agent.build",
                    "agent": "builder",
                    "payload": {"request": request},
                },
                {
                    "title": "Run validation tests",
                    "job_type": "agent.test",
                    "agent": "tester",
                    "payload": {"request": request},
                },
                {
                    "title": "Review final result",
                    "job_type": "agent.review",
                    "agent": "reviewer",
                    "payload": {"request": request},
                },
            ])

        plan = {
            "request": request,
            "steps": steps,
            "step_count": len(steps),
        }

        self.publish("planner.plan.created", plan)
        return plan
