from pathlib import Path

ROOT = Path.cwd()

files = {
    "buster/runtime/inspector.py": r'''from __future__ import annotations

from typing import Any, Dict, List


class RuntimeInspector:
    def __init__(self, core):
        self.core = core

    def runtime_summary(self) -> Dict[str, Any]:
        status = self.core.status()
        return {
            "started": status.get("started"),
            "root": status.get("root"),
            "registry": status.get("registry_summary"),
            "job_count": status.get("jobs", {}).get("count", 0),
            "event_count": len(self.core.events.history),
            "agents": self.core.agents.names(),
            "services": self.core.sdk.registry.names(),
        }

    def services(self) -> Dict[str, Any]:
        return self.core.registry.status().get("services", {})

    def agents(self) -> Dict[str, Any]:
        return self.core.registry.status().get("agents", {})

    def jobs(self) -> Dict[str, Any]:
        return self.core.jobs.status()

    def events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.core.events.recent(limit)

    def blackboard(self) -> Dict[str, Any]:
        return self.core.blackboard.snapshot()

    def agent_memory(self) -> Dict[str, Any]:
        return self.core.agent_memory.status()

    def capabilities(self) -> Dict[str, Any]:
        return self.core.registry.status().get("capabilities", {})

    def full_report(self) -> Dict[str, Any]:
        return {
            "runtime": self.runtime_summary(),
            "services": self.services(),
            "agents": self.agents(),
            "jobs": self.jobs(),
            "capabilities": self.capabilities(),
            "blackboard": self.blackboard(),
            "agent_memory": self.agent_memory(),
            "events": self.events(30),
        }
''',

    "buster/runtime/workflow_graph.py": r'''from __future__ import annotations

from typing import Any, Dict, List


class WorkflowGraphBuilder:
    def __init__(self, core):
        self.core = core

    def from_jobs(self) -> Dict[str, Any]:
        jobs = self.core.jobs.list_jobs()

        nodes = []
        edges = []

        previous_id = None

        for job in jobs:
            job_id = job.get("job_id")
            node = {
                "id": job_id,
                "label": job.get("title"),
                "type": job.get("type"),
                "status": job.get("status"),
            }
            nodes.append(node)

            if previous_id:
                edges.append({
                    "from": previous_id,
                    "to": job_id,
                    "type": "sequence",
                })

            previous_id = job_id

        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "nodes": len(nodes),
                "edges": len(edges),
            },
        }

    def from_recent_events(self, limit: int = 40) -> Dict[str, Any]:
        events = self.core.events.recent(limit)

        nodes = []
        edges = []

        last_agent_event = None

        for index, event in enumerate(events):
            event_id = event.get("id") or f"event_{index}"
            nodes.append({
                "id": event_id,
                "label": event.get("type"),
                "source": event.get("source"),
                "priority": event.get("priority"),
            })

            if last_agent_event:
                edges.append({
                    "from": last_agent_event,
                    "to": event_id,
                    "type": "event_flow",
                })

            last_agent_event = event_id

        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "nodes": len(nodes),
                "edges": len(edges),
            },
        }
''',

    "buster/runtime/plugin_inspector.py": r'''from __future__ import annotations

from typing import Any, Dict


class PluginInspector:
    def __init__(self, core):
        self.core = core

    def status(self) -> Dict[str, Any]:
        host = self.core.service("plugin_host")

        if host is None:
            return {
                "available": False,
                "plugins": {},
                "count": 0,
            }

        if hasattr(host, "status"):
            data = host.status()
            data["available"] = True
            return data

        return {
            "available": True,
            "plugins": {},
            "count": 0,
        }
''',

    "buster/runtime/dev_tools.py": r'''from __future__ import annotations

from typing import Any, Dict

from .inspector import RuntimeInspector
from .plugin_inspector import PluginInspector
from .workflow_graph import WorkflowGraphBuilder


class RuntimeDeveloperTools:
    def __init__(self, core):
        self.core = core
        self.inspector = RuntimeInspector(core)
        self.workflow_graph = WorkflowGraphBuilder(core)
        self.plugins = PluginInspector(core)

    def dashboard_payload(self) -> Dict[str, Any]:
        return {
            "runtime": self.inspector.runtime_summary(),
            "services": self.inspector.services(),
            "agents": self.inspector.agents(),
            "jobs": self.inspector.jobs(),
            "workflow_graph": self.workflow_graph.from_jobs(),
            "event_graph": self.workflow_graph.from_recent_events(25),
            "plugins": self.plugins.status(),
            "events": self.inspector.events(25),
        }
''',

    "buster/runtime/core.py": r'''from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

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
from .inspector import RuntimeInspector
from .workflow_graph import WorkflowGraphBuilder
from .plugin_inspector import PluginInspector
from .dev_tools import RuntimeDeveloperTools

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
    "RuntimeInspector",
    "WorkflowGraphBuilder",
    "PluginInspector",
    "RuntimeDeveloperTools",
]
''',

    "test_v10_6_developer_experience.py": r'''import json

from buster.runtime import create_runtime_core


def main():
    core = create_runtime_core(".")
    core.start()

    core.run("Review architecture quality and validate with tests")

    payload = core.devtools.dashboard_payload()

    print("RUNTIME SUMMARY")
    print(json.dumps(payload["runtime"], indent=4, default=str))

    print()
    print("WORKFLOW GRAPH")
    print(json.dumps(payload["workflow_graph"], indent=4, default=str))

    print()
    print("EVENT GRAPH")
    print(json.dumps(payload["event_graph"]["summary"], indent=4, default=str))

    print()
    print("PLUGINS")
    print(json.dumps(payload["plugins"], indent=4, default=str))


if __name__ == "__main__":
    main()
''',

    "tests/test_v10_6_developer_experience_imports.py": r'''def test_v10_6_developer_experience_imports():
    from buster.runtime import (
        RuntimeInspector,
        WorkflowGraphBuilder,
        PluginInspector,
        RuntimeDeveloperTools,
    )

    assert RuntimeInspector is not None
    assert WorkflowGraphBuilder is not None
    assert PluginInspector is not None
    assert RuntimeDeveloperTools is not None
'''
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created/updated: {rel}")

print()
print("Buster v10.6 Developer Experience added.")
print()
print("Run:")
print("  python test_v10_6_developer_experience.py")
print("  pytest")