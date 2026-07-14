from pathlib import Path

ROOT = Path.cwd()

files = {
    "buster/runtime/blackboard.py": r'''from __future__ import annotations

from typing import Any, Dict, List
from buster.runtime.storage import now


class RuntimeBlackboard:
    def __init__(self, sdk):
        self.sdk = sdk
        self.data: Dict[str, Any] = {
            "goal": None,
            "workspace": {},
            "problems": [],
            "decisions": [],
            "artifacts": [],
            "notes": [],
            "updated_at": now(),
        }

    def set_goal(self, goal: str):
        self.data["goal"] = goal
        self.data["updated_at"] = now()
        self.sdk.publish("blackboard.goal.updated", {"goal": goal}, source="blackboard")
        return self.snapshot()

    def write(self, key: str, value: Any, source: str = "blackboard"):
        self.data[key] = value
        self.data["updated_at"] = now()
        self.sdk.publish("blackboard.updated", {"key": key, "value": value}, source=source)
        return value

    def append(self, key: str, value: Any, source: str = "blackboard"):
        self.data.setdefault(key, [])
        if not isinstance(self.data[key], list):
            self.data[key] = [self.data[key]]
        self.data[key].append(value)
        self.data["updated_at"] = now()
        self.sdk.publish("blackboard.appended", {"key": key, "value": value}, source=source)
        return value

    def read(self, key: str, default=None):
        return self.data.get(key, default)

    def snapshot(self):
        return dict(self.data)
''',

    "buster/runtime/agent_memory.py": r'''from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from buster.runtime.storage import now


class AgentMemory:
    def __init__(self, sdk, path: str | Path = "data/agent_memory.json"):
        self.sdk = sdk
        self.path = Path(path)
        self.data = self._load()

    def _load(self):
        if not self.path.exists():
            return {"agents": {}, "events": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"agents": {}, "events": []}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def record(self, agent: str, action: str, result: Dict[str, Any]):
        profile = self.data.setdefault("agents", {}).setdefault(agent, {
            "runs": 0,
            "successes": 0,
            "failures": 0,
            "last_action": None,
            "last_result": None,
        })

        profile["runs"] += 1
        profile["last_action"] = action
        profile["last_result"] = result

        status = str(result.get("status", "")).lower()
        if status in {"completed", "passed", "success", "ok", "safe_noop"}:
            profile["successes"] += 1
        elif status in {"failed", "error"}:
            profile["failures"] += 1

        event = {
            "agent": agent,
            "action": action,
            "result_status": result.get("status"),
            "timestamp": now(),
        }

        self.data.setdefault("events", []).append(event)
        self.data["events"] = self.data["events"][-500:]

        self.save()
        self.sdk.publish("agent.memory.recorded", event, source="agent_memory")
        return profile

    def status(self):
        return self.data
''',

    "buster/runtime/agent_orchestrator.py": r'''from __future__ import annotations

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
''',

    "buster/runtime/orchestrator_agent.py": r'''from __future__ import annotations

from typing import Any
from .sdk_agent import SDKAgent


class OrchestratorAgent(SDKAgent):
    agent_name = "orchestrator_agent"

    def run(self, task: Any = None):
        orchestrator = self.sdk.require_service("agent_orchestrator")

        if isinstance(task, str):
            return orchestrator.run(task)

        if isinstance(task, dict):
            return orchestrator.run(task.get("request", ""))

        return {
            "status": "idle",
            "message": "Provide a request to orchestrate.",
        }
''',

    "buster/runtime/sdk_bootstrap.py": r'''from __future__ import annotations

from pathlib import Path

from .agent_memory import AgentMemory
from .agent_orchestrator import AgentOrchestrator
from .blackboard import RuntimeBlackboard
from .builder_agent import BuilderAgent
from .fixer_agent import FixerAgent
from .job_agent import JobAgent
from .job_manager import JobManager
from .lifecycle_sdk_agent import LifecycleSDKAgent
from .multi_agent_workflow import MultiAgentWorkflowRunner
from .orchestrator_agent import OrchestratorAgent
from .planner_agent import PlannerAgent
from .registry_agent import RegistryAgent
from .reviewer_agent import ReviewerAgent
from .runtime_registry import RuntimeRegistry
from .sdk_agent_manager import SDKAgentManager
from .sdk_runtime import BusterSDKRuntime
from .tester_agent import TesterAgent


def build_sdk_runtime(root: str | Path = ".", observation_provider=None):
    runtime = BusterSDKRuntime(root=root, observation_provider=observation_provider)
    sdk = runtime.sdk

    registry = RuntimeRegistry(sdk)
    job_manager = JobManager(sdk, registry=registry)
    blackboard = RuntimeBlackboard(sdk)
    memory = AgentMemory(sdk, Path(root) / "data" / "agent_memory.json")

    sdk.register_service("runtime_registry", registry)
    sdk.register_service("job_manager", job_manager)
    sdk.register_service("blackboard", blackboard)
    sdk.register_service("agent_memory", memory)

    agents = SDKAgentManager(sdk)
    agents.register("lifecycle", LifecycleSDKAgent(sdk, root=root))
    agents.register("registry", RegistryAgent(sdk))
    agents.register("jobs", JobAgent(sdk))
    agents.register("planner", PlannerAgent(sdk))
    agents.register("builder", BuilderAgent(sdk))
    agents.register("tester", TesterAgent(sdk))
    agents.register("reviewer", ReviewerAgent(sdk))
    agents.register("fixer", FixerAgent(sdk))

    workflow = MultiAgentWorkflowRunner(sdk, agents, job_manager)
    orchestrator = AgentOrchestrator(sdk, agents, job_manager, registry, blackboard, memory)

    sdk.register_service("agent_manager", agents)
    sdk.register_service("workflow_runner", workflow)
    sdk.register_service("agent_orchestrator", orchestrator)

    agents.register("orchestrator", OrchestratorAgent(sdk))

    registry.register_service("sdk", sdk, capabilities=["events", "config", "registry", "lifecycle"])
    registry.register_service("runtime_engine", runtime.engine, capabilities=["runtime", "tick", "status"])
    registry.register_service("scheduler", runtime.engine.scheduler, capabilities=["schedule", "jobs"])
    registry.register_service("heartbeat", runtime.engine.heartbeat, capabilities=["heartbeat"])
    registry.register_service("watchdog", runtime.engine.watchdog, capabilities=["health"])
    registry.register_service("coordinator", runtime.engine.coordinator, capabilities=["coordination"])
    registry.register_service("intent_prediction", runtime.engine.predictor, capabilities=["intent", "prediction"])
    registry.register_service("runtime_registry", registry, capabilities=["registry", "capabilities"])
    registry.register_service("job_manager", job_manager, capabilities=["jobs", "queue", "tasks"])
    registry.register_service("workflow_runner", workflow, capabilities=["workflow", "multi_agent"])
    registry.register_service("blackboard", blackboard, capabilities=["blackboard", "working_memory"])
    registry.register_service("agent_memory", memory, capabilities=["agent_memory", "learning"])
    registry.register_service("agent_orchestrator", orchestrator, capabilities=["orchestration", "collaboration"])

    registry.register_agent("lifecycle", agents.require("lifecycle"), capabilities=["lifecycle", "health", "backup", "verify"])
    registry.register_agent("registry", agents.require("registry"), capabilities=["registry", "capabilities"])
    registry.register_agent("jobs", agents.require("jobs"), capabilities=["jobs", "tasks"])
    registry.register_agent("planner", agents.require("planner"), capabilities=["planning", "workflow"])
    registry.register_agent("builder", agents.require("builder"), capabilities=["build", "implementation"])
    registry.register_agent("tester", agents.require("tester"), capabilities=["test", "pytest", "validation"])
    registry.register_agent("reviewer", agents.require("reviewer"), capabilities=["review", "quality"])
    registry.register_agent("fixer", agents.require("fixer"), capabilities=["fix", "repair"])
    registry.register_agent("orchestrator", agents.require("orchestrator"), capabilities=["orchestration", "collaboration"])

    registry.register_module("runtime_engine", runtime.engine)

    def lifecycle_health_job(job):
        return agents.run("lifecycle", "health")

    def lifecycle_verify_job(job):
        return agents.run("lifecycle", "verify")

    def agent_build_job(job):
        return agents.run("builder", job.get("payload", {}))

    def agent_test_job(job):
        return agents.run("tester", job.get("payload", {}))

    def agent_review_job(job):
        return agents.run("reviewer", job.get("payload", {}))

    def agent_fix_job(job):
        return agents.run("fixer", job.get("payload", {}))

    job_manager.register_handler("lifecycle.health", lifecycle_health_job)
    job_manager.register_handler("lifecycle.verify", lifecycle_verify_job)
    job_manager.register_handler("agent.build", agent_build_job)
    job_manager.register_handler("agent.test", agent_test_job)
    job_manager.register_handler("agent.review", agent_review_job)
    job_manager.register_handler("agent.fix", agent_fix_job)

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
        "workflow": workflow,
        "blackboard": blackboard,
        "agent_memory": memory,
        "orchestrator": orchestrator,
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
]
''',

    "test_v10_4_collaborative_intelligence.py": r'''import json

from buster.runtime.sdk_bootstrap import build_sdk_runtime


def main():
    system = build_sdk_runtime(".")
    runtime = system["runtime"]
    orchestrator = system["orchestrator"]
    registry = system["registry"]
    blackboard = system["blackboard"]
    memory = system["agent_memory"]
    sdk = system["sdk"]

    runtime.start()

    result = orchestrator.run(
        "Build a safe runtime feature, validate it, review architecture quality"
    )

    print("REGISTRY")
    print(json.dumps(registry.status()["summary"], indent=4, default=str))

    print()
    print("ORCHESTRATION RESULT")
    print(json.dumps({
        "status": result["status"],
        "selected_agents": result["selected_agents"],
        "jobs": len(result["jobs"]),
    }, indent=4, default=str))

    print()
    print("BLACKBOARD")
    print(json.dumps(blackboard.snapshot(), indent=4, default=str))

    print()
    print("AGENT MEMORY")
    print(json.dumps(memory.status(), indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(sdk.events.recent(30), indent=4, default=str))


if __name__ == "__main__":
    main()
''',

    "tests/test_v10_4_collaborative_intelligence_imports.py": r'''def test_v10_4_collaborative_intelligence_imports():
    from buster.runtime import (
        RuntimeBlackboard,
        AgentMemory,
        AgentOrchestrator,
        OrchestratorAgent,
    )

    assert RuntimeBlackboard is not None
    assert AgentMemory is not None
    assert AgentOrchestrator is not None
    assert OrchestratorAgent is not None
'''
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created/updated: {rel}")

print()
print("Buster v10.4 Collaborative Intelligence added.")
print()
print("Run:")
print("  python test_v10_4_collaborative_intelligence.py")
print("  pytest")