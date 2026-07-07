from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .sdk_bootstrap import build_sdk_runtime


class BusterRuntimeCore:
    """
    Buster v10.5 Runtime Core.

    One central access point for:

    - SDK
    - Event API
    - Runtime Engine
    - Runtime Registry
    - Job Manager
    - Agent Manager
    - Blackboard
    - Agent Memory
    - Orchestrator
    - Workflow Runner
    """

    def __init__(self, root: str | Path = ".", observation_provider=None):
        self.root = Path(root).resolve()
        self.system = build_sdk_runtime(
            root=self.root,
            observation_provider=observation_provider,
        )

        self.runtime = self.system["runtime"]
        self.sdk = self.system["sdk"]
        self.events = self.sdk.events
        self.services = self.sdk.registry

        self.agents = self.system["agents"]
        self.registry = self.system["registry"]
        self.jobs = self.system["jobs"]
        self.workflow = self.system["workflow"]
        self.blackboard = self.system["blackboard"]
        self.agent_memory = self.system["agent_memory"]
        self.orchestrator = self.system["orchestrator"]

        self.started = False

    def start(self) -> Dict[str, Any]:
        result = self.runtime.start()
        self.started = True
        self.events.publish(
            "runtime.core.started",
            {"root": str(self.root)},
            source="runtime_core",
        )
        return result

    def stop(self) -> Dict[str, Any]:
        result = self.runtime.stop()
        self.started = False
        self.events.publish(
            "runtime.core.stopped",
            {"root": str(self.root)},
            source="runtime_core",
        )
        return result

    def tick(self, observations=None) -> Dict[str, Any]:
        return self.runtime.tick_once(observations)

    def run(self, request: str) -> Dict[str, Any]:
        self.events.publish(
            "runtime.core.request.received",
            {"request": request},
            source="runtime_core",
        )
        return self.orchestrator.run(request)

    def run_agent(self, name: str, task: Any = None) -> Any:
        return self.agents.run(name, task)

    def create_job(self, title: str, job_type: str = "generic", payload=None):
        return self.jobs.create_job(title=title, job_type=job_type, payload=payload or {})

    def run_job(self, job_id: str):
        return self.jobs.run_job(job_id)

    def service(self, name: str, default=None):
        return self.sdk.service(name, default)

    def require_service(self, name: str):
        return self.sdk.require_service(name)

    def status(self) -> Dict[str, Any]:
        registry_status = self.registry.status()
        job_status = self.jobs.status()
        memory_status = self.agent_memory.status()

        return {
            "root": str(self.root),
            "started": self.started,
            "runtime": self.runtime.status(),
            "sdk": self.sdk.status(),
            "registry_summary": registry_status.get("summary", {}),
            "jobs": job_status,
            "agents": self.agents.status(),
            "blackboard": self.blackboard.snapshot(),
            "agent_memory": memory_status,
            "recent_events": self.events.recent(20),
        }


def create_runtime_core(root: str | Path = ".", observation_provider=None) -> BusterRuntimeCore:
    return BusterRuntimeCore(root=root, observation_provider=observation_provider)
