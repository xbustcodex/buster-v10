from pathlib import Path

ROOT = Path.cwd()

files = {
    "buster/runtime/core.py": r'''from __future__ import annotations

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
from .planner_agent import PlannerAgent
from .builder_agent import BuilderAgent
from .tester_agent import TesterAgent
from .reviewer_agent import ReviewerAgent
from .fixer_agent import FixerAgent
from .multi_agent_workflow import MultiAgentWorkflowRunner
from .blackboard import RuntimeBlackboard
from .agent_memory import AgentMemory
from .agent_orchestrator import AgentOrchestrator
from .orchestrator_agent import OrchestratorAgent
from .core import BusterRuntimeCore, create_runtime_core

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
    "PlannerAgent",
    "BuilderAgent",
    "TesterAgent",
    "ReviewerAgent",
    "FixerAgent",
    "MultiAgentWorkflowRunner",
    "RuntimeBlackboard",
    "AgentMemory",
    "AgentOrchestrator",
    "OrchestratorAgent",
    "BusterRuntimeCore",
    "create_runtime_core",
]
''',

    "buster/runtime/plugin_api.py": r'''from __future__ import annotations

from typing import Protocol, Any


class BusterPlugin(Protocol):
    name: str
    version: str

    def register(self, runtime) -> Any:
        ...


class PluginHost:
    def __init__(self, runtime):
        self.runtime = runtime
        self.plugins = {}

    def register_plugin(self, plugin):
        name = getattr(plugin, "name", plugin.__class__.__name__)
        result = plugin.register(self.runtime)
        self.plugins[name] = {
            "name": name,
            "version": getattr(plugin, "version", "0.0.0"),
            "plugin": plugin,
            "result": result,
        }

        self.runtime.events.publish(
            "plugin.registered",
            {
                "name": name,
                "version": self.plugins[name]["version"],
            },
            source="plugin_host",
        )

        return result

    def status(self):
        return {
            "count": len(self.plugins),
            "plugins": {
                name: {
                    "version": data["version"],
                    "result": data["result"],
                }
                for name, data in self.plugins.items()
            },
        }
''',

    "test_v10_5_runtime_core.py": r'''import json

from buster.runtime import create_runtime_core


def main():
    core = create_runtime_core(".")

    print("START")
    print(json.dumps(core.start(), indent=4, default=str))

    print()
    print("CORE STATUS")
    print(json.dumps({
        "started": core.status()["started"],
        "registry_summary": core.status()["registry_summary"],
        "services": core.sdk.registry.names(),
        "agents": core.agents.names(),
    }, indent=4, default=str))

    print()
    print("RUN ORCHESTRATED REQUEST")
    result = core.run("Review architecture quality and validate with tests")
    print(json.dumps({
        "status": result["status"],
        "selected_agents": result["selected_agents"],
        "jobs": len(result["jobs"]),
    }, indent=4, default=str))

    print()
    print("BLACKBOARD GOAL")
    print(json.dumps(core.blackboard.read("goal"), indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(core.events.recent(20), indent=4, default=str))


if __name__ == "__main__":
    main()
''',

    "tests/test_v10_5_runtime_core_imports.py": r'''def test_v10_5_runtime_core_imports():
    from buster.runtime import BusterRuntimeCore, create_runtime_core
    from buster.runtime.plugin_api import PluginHost

    assert BusterRuntimeCore is not None
    assert create_runtime_core is not None
    assert PluginHost is not None
'''
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created/updated: {rel}")

print()
print("Buster v10.5 Runtime Core added.")
print()
print("Run:")
print("  python test_v10_5_runtime_core.py")
print("  pytest")