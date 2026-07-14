from pathlib import Path

ROOT = Path.cwd()

files = {
    "buster/runtime/runtime_registry.py": r'''from __future__ import annotations

from typing import Any, Dict, List
from buster.runtime.storage import now


class RuntimeRegistry:
    """
    Runtime-wide registry for v10.

    This is the self-describing map of Buster:
    - services
    - agents
    - modules
    - jobs
    - capabilities
    - runtime health/state
    """

    def __init__(self, sdk):
        self.sdk = sdk
        self.services: Dict[str, Dict[str, Any]] = {}
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.modules: Dict[str, Dict[str, Any]] = {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.capabilities: Dict[str, List[str]] = {}
        self.created_at = now()

    def register_service(self, name: str, service: Any, capabilities=None):
        capabilities = capabilities or []

        self.services[name] = {
            "name": name,
            "type": service.__class__.__name__,
            "capabilities": list(capabilities),
            "registered_at": now(),
        }

        for capability in capabilities:
            self.capabilities.setdefault(capability, [])
            if name not in self.capabilities[capability]:
                self.capabilities[capability].append(name)

        self.sdk.publish(
            "registry.service.registered",
            {
                "name": name,
                "capabilities": list(capabilities),
            },
            source="runtime_registry",
        )

    def register_agent(self, name: str, agent: Any, capabilities=None):
        capabilities = capabilities or []

        self.agents[name] = {
            "name": name,
            "type": agent.__class__.__name__,
            "capabilities": list(capabilities),
            "registered_at": now(),
        }

        self.sdk.publish(
            "registry.agent.registered",
            {
                "name": name,
                "capabilities": list(capabilities),
            },
            source="runtime_registry",
        )

    def register_module(self, name: str, module: Any):
        self.modules[name] = {
            "name": name,
            "type": module.__class__.__name__,
            "registered_at": now(),
        }

        self.sdk.publish(
            "registry.module.registered",
            {"name": name},
            source="runtime_registry",
        )

    def register_job(self, job_id: str, job_data: Dict[str, Any]):
        self.jobs[job_id] = dict(job_data)

        self.sdk.publish(
            "registry.job.registered",
            {
                "job_id": job_id,
                "status": job_data.get("status"),
                "title": job_data.get("title"),
            },
            source="runtime_registry",
        )

    def update_job(self, job_id: str, updates: Dict[str, Any]):
        if job_id not in self.jobs:
            self.jobs[job_id] = {"job_id": job_id}

        self.jobs[job_id].update(updates)
        self.jobs[job_id]["updated_at"] = now()

        self.sdk.publish(
            "registry.job.updated",
            {
                "job_id": job_id,
                "status": self.jobs[job_id].get("status"),
            },
            source="runtime_registry",
        )

    def services_for_capability(self, capability: str) -> List[str]:
        return list(self.capabilities.get(capability, []))

    def status(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "services": self.services,
            "agents": self.agents,
            "modules": self.modules,
            "jobs": self.jobs,
            "capabilities": self.capabilities,
            "summary": {
                "services": len(self.services),
                "agents": len(self.agents),
                "modules": len(self.modules),
                "jobs": len(self.jobs),
                "capabilities": len(self.capabilities),
            },
        }
''',

    "buster/runtime/job_manager.py": r'''from __future__ import annotations

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
''',

    "buster/runtime/job_agent.py": r'''from __future__ import annotations

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
''',

    "buster/runtime/registry_agent.py": r'''from __future__ import annotations

from typing import Any

from .sdk_agent import SDKAgent


class RegistryAgent(SDKAgent):
    agent_name = "registry_agent"

    def run(self, task: Any = None):
        registry = self.sdk.require_service("runtime_registry")

        if task is None or task == "status":
            return registry.status()

        if isinstance(task, dict):
            action = task.get("action", "status")

            if action == "capability":
                return {
                    "capability": task.get("capability"),
                    "services": registry.services_for_capability(task.get("capability")),
                }

        return registry.status()
''',

    "buster/runtime/sdk_bootstrap.py": r'''from __future__ import annotations

from pathlib import Path

from .job_agent import JobAgent
from .job_manager import JobManager
from .lifecycle_sdk_agent import LifecycleSDKAgent
from .registry_agent import RegistryAgent
from .runtime_registry import RuntimeRegistry
from .sdk_agent_manager import SDKAgentManager
from .sdk_runtime import BusterSDKRuntime


def build_sdk_runtime(root: str | Path = ".", observation_provider=None):
    runtime = BusterSDKRuntime(root=root, observation_provider=observation_provider)
    sdk = runtime.sdk

    registry = RuntimeRegistry(sdk)
    job_manager = JobManager(sdk, registry=registry)

    sdk.register_service("runtime_registry", registry)
    sdk.register_service("job_manager", job_manager)

    agents = SDKAgentManager(sdk)
    agents.register("lifecycle", LifecycleSDKAgent(sdk, root=root))
    agents.register("registry", RegistryAgent(sdk))
    agents.register("jobs", JobAgent(sdk))

    sdk.register_service("agent_manager", agents)

    registry.register_service("sdk", sdk, capabilities=["events", "config", "registry", "lifecycle"])
    registry.register_service("runtime_engine", runtime.engine, capabilities=["runtime", "tick", "status"])
    registry.register_service("scheduler", runtime.engine.scheduler, capabilities=["schedule", "jobs"])
    registry.register_service("heartbeat", runtime.engine.heartbeat, capabilities=["heartbeat"])
    registry.register_service("watchdog", runtime.engine.watchdog, capabilities=["health"])
    registry.register_service("coordinator", runtime.engine.coordinator, capabilities=["coordination"])
    registry.register_service("intent_prediction", runtime.engine.predictor, capabilities=["intent", "prediction"])
    registry.register_service("runtime_registry", registry, capabilities=["registry", "capabilities"])
    registry.register_service("job_manager", job_manager, capabilities=["jobs", "queue", "tasks"])

    registry.register_agent("lifecycle", agents.require("lifecycle"), capabilities=["lifecycle", "health", "backup", "verify"])
    registry.register_agent("registry", agents.require("registry"), capabilities=["registry", "capabilities"])
    registry.register_agent("jobs", agents.require("jobs"), capabilities=["jobs", "tasks"])

    registry.register_module("runtime_engine", runtime.engine)

    def lifecycle_health_job(job):
        return agents.run("lifecycle", "health")

    def lifecycle_verify_job(job):
        return agents.run("lifecycle", "verify")

    job_manager.register_handler("lifecycle.health", lifecycle_health_job)
    job_manager.register_handler("lifecycle.verify", lifecycle_verify_job)

    sdk.publish(
        "runtime.bootstrap.completed",
        {
            "services": sdk.registry.names(),
            "agents": agents.names(),
            "runtime_registry": registry.status()["summary"],
        },
        source="sdk_bootstrap",
    )

    return {
        "runtime": runtime,
        "sdk": sdk,
        "agents": agents,
        "registry": registry,
        "jobs": job_manager,
    }
''',

    "buster/runtime/__init__.py": r'''from .engine import BusterRuntimeEngine
from .heartbeat import RuntimeHeartbeat
from .scheduler import RuntimeScheduler
from .dispatcher import RuntimeDispatcher
from .lifecycle import RuntimeLifecycle
from .watchdog import RuntimeWatchdog
from .coordinator import RuntimeCoordinator
from .idle_manager import IdleManager
from .intent_prediction import IntentPredictionEngine

from .sdk_runtime import BusterSDKRuntime
from .sdk_bootstrap import build_sdk_runtime
from .sdk_agent_manager import SDKAgentManager
from .lifecycle_sdk_agent import LifecycleSDKAgent
from .runtime_registry import RuntimeRegistry
from .job_manager import JobManager, JobStatus

__all__ = [
    "BusterRuntimeEngine",
    "RuntimeHeartbeat",
    "RuntimeScheduler",
    "RuntimeDispatcher",
    "RuntimeLifecycle",
    "RuntimeWatchdog",
    "RuntimeCoordinator",
    "IdleManager",
    "IntentPredictionEngine",
    "BusterSDKRuntime",
    "build_sdk_runtime",
    "SDKAgentManager",
    "LifecycleSDKAgent",
    "RuntimeRegistry",
    "JobManager",
    "JobStatus",
]
''',

    "test_v10_1_runtime_registry_jobs.py": r'''import json

from buster.runtime.sdk_bootstrap import build_sdk_runtime


def main():
    system = build_sdk_runtime(".")
    runtime = system["runtime"]
    sdk = system["sdk"]
    agents = system["agents"]
    registry = system["registry"]
    jobs = system["jobs"]

    runtime.start()

    print("REGISTRY STATUS")
    print(json.dumps(registry.status()["summary"], indent=4, default=str))

    print()
    print("CAPABILITY: health")
    print(json.dumps(
        agents.run("registry", {"action": "capability", "capability": "health"}),
        indent=4,
        default=str,
    ))

    print()
    print("CREATE JOB")
    job = agents.run("jobs", {
        "action": "create",
        "title": "Run lifecycle health check",
        "job_type": "lifecycle.health",
        "payload": {"requested_by": "v10.1_test"},
    })
    print(json.dumps(job, indent=4, default=str))

    print()
    print("RUN JOB")
    completed = agents.run("jobs", {
        "action": "run",
        "job_id": job["job_id"],
    })
    print(json.dumps(completed, indent=4, default=str))

    print()
    print("JOB MANAGER STATUS")
    print(json.dumps(jobs.status(), indent=4, default=str))

    print()
    print("REGISTRY JOBS")
    print(json.dumps(registry.status()["jobs"], indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(sdk.events.recent(25), indent=4, default=str))


if __name__ == "__main__":
    main()
'''
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created/updated: {rel}")

print()
print("Buster v10.1 Runtime Registry + Job System added.")
print()
print("Run:")
print("  python test_v10_1_runtime_registry_jobs.py")
print("  pytest")