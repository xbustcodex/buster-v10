from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from .dispatcher import RuntimeDispatcher
from .state_store import RuntimeStateStore

from .sdk_bootstrap import build_sdk_runtime


class BusterRuntimeCore:
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

        from .dev_tools import RuntimeDeveloperTools
        self.devtools = RuntimeDeveloperTools(self)
        
        self.state = RuntimeStateStore()
        self.dispatcher = RuntimeDispatcher(self.state)

        self.started = False
        self.dispatcher = RuntimeDispatcher()

    def start(self) -> Dict[str, Any]:
        result = self.runtime.start()
        self.started = True
        event = {
            "root": str(self.root),
            "started": True,
        }

        self.events.publish(
            "runtime.core.started",
            event,
            source="runtime_core",
        )

        self.dispatcher.publish(
            "runtime.started",
            event,
            source="runtime_core",
        )
        return result
        self.refresh_state()

    def stop(self) -> Dict[str, Any]:
        result = self.runtime.stop()
        self.started = False
        event = {
            "root": str(self.root),
            "started": False,
        }

        self.events.publish(
            "runtime.core.stopped",
            event,
            source="runtime_core",
        )

        self.dispatcher.publish(
            "runtime.stopped",
            event,
            source="runtime_core",
        )
        return result

    def tick(self, observations=None) -> Dict[str, Any]:

        result = self.runtime.tick_once(observations)

        self.dispatcher.publish(
            "runtime.tick",
            result,
            source="runtime_core",
        )
        self.refresh_state()
        return result
        

    def run(self, request: str) -> Dict[str, Any]:
        event = {
            "request": request,
        }

        self.events.publish(
            "runtime.core.request.received",
            event,
            source="runtime_core",
        )

        self.dispatcher.publish(
            "runtime.request",
            event,
            source="runtime_core",
        )
        return self.orchestrator.run(request)

    def run_agent(self, name, task=None):

        self.dispatcher.publish(
            "agent.started",
            {
                "agent": name,
            },
            source="runtime_core",
        )

        result = self.agents.run(name, task)

        self.dispatcher.publish(
            "agent.finished",
            {
                "agent": name,
                "result": result,
            },
            source="runtime_core",
        )
        self.refresh_state()
        return result

    def create_job(self, title, job_type="generic", payload=None):

        job = self.jobs.create_job(
            title=title,
            job_type=job_type,
            payload=payload or {},
        )

        self.dispatcher.publish(
            "job.created",
            job,
            source="runtime_core",
        )

        return job
        
    def run_job(self, job_id):

        self.dispatcher.publish(
            "job.started",
            {"job_id": job_id},
            source="runtime_core",
        )

        result = self.jobs.run_job(job_id)

        self.dispatcher.publish(
            "job.finished",
            {
                "job_id": job_id,
                "result": result,
            },
            source="runtime_core",
        )
        self.refresh_state()
        return result

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
            "state": self.state.snapshot(),
            "dispatcher": self.dispatcher.status(),
        }
        
    def notify(self, title, message, level="info"):

        self.dispatcher.publish(
            "notification",
            {
                "title": title,
                "message": message,
                "level": level,
            },
            source="runtime_core",
        )    
        
        
    def refresh_state(self) -> Dict[str, Any]:
        snapshot = {
            "runtime": {
                "started": self.started,
                "status": "running" if self.started else "ready",
                "root": str(self.root),
                "details": self.runtime.status(),
            },
            "jobs": self.jobs.status(),
            "agents": self.agents.status(),
            "memory": self.agent_memory.status(),
            "blackboard": self.blackboard.snapshot(),
            "registry": self.registry.status(),
            "services": self.sdk.status(),
        }

        for key, value in snapshot.items():
            self.state.set(key, value)

        return self.state.snapshot()    


def create_runtime_core(root: str | Path = ".", observation_provider=None) -> BusterRuntimeCore:
    return BusterRuntimeCore(root=root, observation_provider=observation_provider)
