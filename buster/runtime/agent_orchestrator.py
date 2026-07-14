from __future__ import annotations

from typing import Any, Dict, List


class AgentOrchestrator:
    """
    Coordinates the planner, job manager and runtime agents.

    The orchestrator returns both:

    - message: concise user-facing text for Chat
    - result: complete internal runtime data for Mission Control,
      Timeline, plugins and developer tools
    """

    def __init__(
        self,
        sdk,
        agents,
        jobs,
        registry,
        blackboard,
        memory,
    ):
        self.sdk = sdk
        self.agents = agents
        self.jobs = jobs
        self.registry = registry
        self.blackboard = blackboard
        self.memory = memory

    def choose_agents(self, request: str) -> List[str]:
        text = str(request or "").lower()
        selected = ["planner"]

        if any(
            keyword in text
            for keyword in (
                "build",
                "create",
                "feature",
                "implement",
                "generate",
            )
        ):
            selected.append("builder")

        if any(
            keyword in text
            for keyword in (
                "test",
                "validate",
                "pytest",
                "verify",
            )
        ):
            selected.append("tester")

        if any(
            keyword in text
            for keyword in (
                "review",
                "quality",
                "architecture",
                "inspect",
            )
        ):
            selected.append("reviewer")

        if any(
            keyword in text
            for keyword in (
                "fix",
                "error",
                "failed",
                "repair",
                "bug",
            )
        ):
            selected.append("fixer")

        if any(
            keyword in text
            for keyword in (
                "health",
                "lifecycle",
                "diagnostic",
            )
        ):
            selected.append("lifecycle")

        return list(dict.fromkeys(selected))

    def run(self, request: str) -> Dict[str, Any]:
        request = str(request or "").strip()

        if not request:
            return {
                "status": "idle",
                "message": "Please provide a request.",
                "result": {
                    "request": "",
                    "selected_agents": [],
                    "plan": {},
                    "jobs": [],
                    "status": "idle",
                },
            }

        self.blackboard.set_goal(request)

        selected_agents = self.choose_agents(request)

        self.sdk.publish(
            "orchestrator.started",
            {
                "request": request,
                "agents": selected_agents,
            },
            source="agent_orchestrator",
        )

        try:
            plan = self.agents.run(
                "planner",
                {
                    "request": request,
                },
            )
        except Exception as exc:
            return self._failure_response(
                request=request,
                selected_agents=selected_agents,
                stage="planning",
                error=exc,
            )

        if not isinstance(plan, dict):
            plan = {
                "request": request,
                "steps": [],
                "step_count": 0,
                "raw_result": plan,
            }

        self.memory.record(
            "planner",
            "plan",
            {
                "status": "completed",
                "plan": plan,
            },
        )

        self.blackboard.write(
            "plan",
            plan,
            source="agent_orchestrator",
        )

        results: List[Dict[str, Any]] = []

        for step_number, step in enumerate(
            plan.get("steps", []),
            start=1,
        ):
            if not isinstance(step, dict):
                continue

            title = str(
                step.get("title")
                or f"Workflow step {step_number}"
            )

            job_type = str(
                step.get("job_type")
                or "generic"
            )

            agent_name = str(
                step.get("agent")
                or "unknown"
            )

            payload = step.get("payload", {})

            if not isinstance(payload, dict):
                payload = {
                    "value": payload,
                }

            self.sdk.publish(
                "orchestrator.step.started",
                {
                    "request": request,
                    "step": step_number,
                    "title": title,
                    "job_type": job_type,
                    "agent": agent_name,
                },
                source="agent_orchestrator",
            )

            try:
                job = self.agents.run(
                    "jobs",
                    {
                        "action": "create",
                        "title": title,
                        "job_type": job_type,
                        "payload": payload,
                    },
                )

                if not isinstance(job, dict):
                    raise RuntimeError(
                        "Job creation did not return a dictionary."
                    )

                job_id = job.get("job_id")

                if not job_id:
                    raise RuntimeError(
                        "Job creation did not return a job_id."
                    )

                completed = self.agents.run(
                    "jobs",
                    {
                        "action": "run",
                        "job_id": job_id,
                    },
                )

                if not isinstance(completed, dict):
                    completed = {
                        "job_id": job_id,
                        "status": "completed",
                        "result": completed,
                    }

            except Exception as exc:
                completed = {
                    "status": "failed",
                    "title": title,
                    "job_type": job_type,
                    "agent": agent_name,
                    "result": {
                        "status": "failed",
                        "error": str(exc),
                    },
                }

            results.append(completed)

            self.blackboard.append(
                "artifacts",
                completed,
                source="agent_orchestrator",
            )

            result_payload = completed.get("result") or {}

            if not isinstance(result_payload, dict):
                result_payload = {
                    "value": result_payload,
                }

            self.memory.record(
                agent_name,
                job_type,
                result_payload,
            )

            step_failed = self._is_failed_result(
                completed,
                result_payload,
            )

            self.sdk.publish(
                (
                    "orchestrator.step.failed"
                    if step_failed
                    else "orchestrator.step.finished"
                ),
                {
                    "request": request,
                    "step": step_number,
                    "title": title,
                    "job_type": job_type,
                    "agent": agent_name,
                    "status": (
                        "failed"
                        if step_failed
                        else "completed"
                    ),
                },
                source="agent_orchestrator",
            )

            if step_failed:
                self.blackboard.append(
                    "problems",
                    result_payload,
                    source="agent_orchestrator",
                )
                break

        final_status = self._final_status(results)

        internal_result = {
            "request": request,
            "selected_agents": selected_agents,
            "plan": plan,
            "jobs": results,
            "status": final_status,
            "blackboard": self.blackboard.snapshot(),
            "agent_memory": self.memory.status(),
        }

        message = self._build_user_message(
            request=request,
            selected_agents=selected_agents,
            plan=plan,
            results=results,
            final_status=final_status,
        )

        response = {
            "status": final_status,
            "message": message,
            "result": internal_result,
        }

        self.sdk.publish(
            "orchestrator.finished",
            {
                "request": request,
                "status": final_status,
                "jobs": len(results),
                "message": message,
            },
            source="agent_orchestrator",
        )

        return response

    def _is_failed_result(
        self,
        completed: Dict[str, Any],
        result_payload: Dict[str, Any],
    ) -> bool:
        completed_status = str(
            completed.get("status", "")
        ).lower()

        result_status = str(
            result_payload.get("status", "")
        ).lower()

        return completed_status in {
            "failed",
            "error",
        } or result_status in {
            "failed",
            "error",
        }

    def _final_status(
        self,
        results: List[Dict[str, Any]],
    ) -> str:
        for item in results:
            payload = item.get("result") or {}

            if not isinstance(payload, dict):
                payload = {}

            if self._is_failed_result(
                item,
                payload,
            ):
                return "failed"

        return "completed"

    def _build_user_message(
        self,
        request: str,
        selected_agents: List[str],
        plan: Dict[str, Any],
        results: List[Dict[str, Any]],
        final_status: str,
    ) -> str:
        lines: List[str] = []

        if final_status == "failed":
            lines.append("The runtime workflow encountered a problem.")
        else:
            lines.append("The runtime workflow completed successfully.")

        lines.append("")
        lines.append(f"Request: {request}")

        if selected_agents:
            readable_agents = ", ".join(
                agent.replace("_", " ").title()
                for agent in selected_agents
            )

            lines.append(
                f"Agents involved: {readable_agents}"
            )

        step_count = int(
            plan.get(
                "step_count",
                len(plan.get("steps", [])),
            )
            or 0
        )

        lines.append(
            f"Planned steps: {step_count}"
        )

        if results:
            lines.append("")
            lines.append("Results:")

            for index, item in enumerate(
                results,
                start=1,
            ):
                lines.append(
                    self._summarize_job(
                        item,
                        index,
                    )
                )
        elif step_count == 0:
            lines.append("")
            lines.append(
                "The planner did not create any executable steps."
            )

        return "\n".join(lines)

    def _summarize_job(
        self,
        item: Dict[str, Any],
        index: int,
    ) -> str:
        result = item.get("result") or {}

        if not isinstance(result, dict):
            result = {
                "value": result,
            }

        title = str(
            item.get("title")
            or item.get("name")
            or item.get("job_type")
            or result.get("title")
            or f"Step {index}"
        )

        status = str(
            result.get("status")
            or item.get("status")
            or "completed"
        ).lower()

        if status in {
            "failed",
            "error",
        }:
            error = (
                result.get("error")
                or result.get("message")
                or item.get("error")
                or "Unknown error"
            )

            return (
                f"• {title}: Failed — {error}"
            )

        summary = self._extract_result_text(result)

        if summary:
            return (
                f"• {title}: {summary}"
            )

        return (
            f"• {title}: Completed"
        )

    def _extract_result_text(
        self,
        result: Dict[str, Any],
    ) -> str:
        for key in (
            "summary",
            "message",
            "output",
            "response",
            "recommendation",
        ):
            value = result.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        if "returncode" in result:
            return (
                f"Completed with return code "
                f"{result.get('returncode')}."
            )

        if "files_created" in result:
            files = result.get("files_created")

            if isinstance(files, list):
                return (
                    f"Created {len(files)} file"
                    f"{'' if len(files) == 1 else 's'}."
                )

        return ""

    def _failure_response(
        self,
        request: str,
        selected_agents: List[str],
        stage: str,
        error: Exception,
    ) -> Dict[str, Any]:
        message = (
            f"The runtime failed during {stage}: {error}"
        )

        result = {
            "request": request,
            "selected_agents": selected_agents,
            "plan": {},
            "jobs": [],
            "status": "failed",
            "error": str(error),
            "stage": stage,
            "blackboard": self.blackboard.snapshot(),
            "agent_memory": self.memory.status(),
        }

        self.sdk.publish(
            "orchestrator.failed",
            {
                "request": request,
                "stage": stage,
                "error": str(error),
            },
            source="agent_orchestrator",
        )

        return {
            "status": "failed",
            "message": message,
            "result": result,
        }