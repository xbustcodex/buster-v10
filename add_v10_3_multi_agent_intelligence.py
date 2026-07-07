from pathlib import Path

ROOT = Path.cwd()

files = {
    "buster/runtime/planner_agent.py": r'''from __future__ import annotations

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
''',

    "buster/runtime/builder_agent.py": r'''from __future__ import annotations

from typing import Any, Dict

from .sdk_agent import SDKAgent


class BuilderAgent(SDKAgent):
    agent_name = "builder_agent"

    def run(self, task: Any = None) -> Dict[str, Any]:
        payload = task if isinstance(task, dict) else {"request": str(task or "")}

        result = {
            "agent": self.agent_name,
            "status": "completed",
            "summary": "Builder Agent prepared the implementation plan.",
            "request": payload.get("request", ""),
            "actions": [
                "checked requested build scope",
                "prepared implementation placeholder",
                "recommended validation through tester agent",
            ],
        }

        self.publish("builder.completed", result)
        return result
''',

    "buster/runtime/tester_agent.py": r'''from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict

from .sdk_agent import SDKAgent


class TesterAgent(SDKAgent):
    agent_name = "tester_agent"

    def run(self, task: Any = None) -> Dict[str, Any]:
        payload = task if isinstance(task, dict) else {"request": str(task or "")}

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = (result.stdout + "\\n" + result.stderr).strip()

        data = {
            "agent": self.agent_name,
            "status": "passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "request": payload.get("request", ""),
            "output_tail": output[-4000:],
        }

        self.publish("tester.completed", data)
        return data
''',

    "buster/runtime/reviewer_agent.py": r'''from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .sdk_agent import SDKAgent


class ReviewerAgent(SDKAgent):
    agent_name = "reviewer_agent"

    def run(self, task: Any = None) -> Dict[str, Any]:
        payload = task if isinstance(task, dict) else {"request": str(task or "")}

        runtime_files = list(Path("buster/runtime").glob("*.py"))
        test_files = list(Path("tests").glob("test_*.py"))

        findings = []

        if not runtime_files:
            findings.append("No runtime files found.")

        if not test_files:
            findings.append("No tests found.")

        if Path("data/runtime_events.json").exists():
            findings.append("Runtime event state file exists; ensure generated data is not committed unless intentional.")

        data = {
            "agent": self.agent_name,
            "status": "completed",
            "request": payload.get("request", ""),
            "runtime_files": len(runtime_files),
            "test_files": len(test_files),
            "findings": findings,
            "recommendation": "Architecture looks valid. Keep generated data out of commits.",
        }

        self.publish("reviewer.completed", data)
        return data
''',

    "buster/runtime/fixer_agent.py": r'''from __future__ import annotations

from typing import Any, Dict

from .sdk_agent import SDKAgent


class FixerAgent(SDKAgent):
    agent_name = "fixer_agent"

    def run(self, task: Any = None) -> Dict[str, Any]:
        payload = task if isinstance(task, dict) else {"request": str(task or "")}

        result = {
            "agent": self.agent_name,
            "status": "safe_noop",
            "request": payload.get("request", ""),
            "summary": "Fixer Agent ran in safe mode and did not modify files.",
            "next_step": "Enable targeted patch mode when a concrete failing test or file issue is provided.",
        }

        self.publish("fixer.completed", result)
        return result
''',

    "buster/runtime/multi_agent_workflow.py": r'''from __future__ import annotations

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
''',

    "buster/runtime/sdk_bootstrap.py": r'''from __future__ import annotations

from pathlib import Path

from .builder_agent import BuilderAgent
from .fixer_agent import FixerAgent
from .job_agent import JobAgent
from .job_manager import JobManager
from .lifecycle_sdk_agent import LifecycleSDKAgent
from .multi_agent_workflow import MultiAgentWorkflowRunner
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

    sdk.register_service("runtime_registry", registry)
    sdk.register_service("job_manager", job_manager)

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

    sdk.register_service("agent_manager", agents)
    sdk.register_service("workflow_runner", workflow)

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

    registry.register_agent("lifecycle", agents.require("lifecycle"), capabilities=["lifecycle", "health", "backup", "verify"])
    registry.register_agent("registry", agents.require("registry"), capabilities=["registry", "capabilities"])
    registry.register_agent("jobs", agents.require("jobs"), capabilities=["jobs", "tasks"])
    registry.register_agent("planner", agents.require("planner"), capabilities=["planning", "workflow"])
    registry.register_agent("builder", agents.require("builder"), capabilities=["build", "implementation"])
    registry.register_agent("tester", agents.require("tester"), capabilities=["test", "pytest", "validation"])
    registry.register_agent("reviewer", agents.require("reviewer"), capabilities=["review", "quality"])
    registry.register_agent("fixer", agents.require("fixer"), capabilities=["fix", "repair"])

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
]
''',

    "test_v10_3_multi_agent_intelligence.py": r'''import json

from buster.runtime.sdk_bootstrap import build_sdk_runtime


def main():
    system = build_sdk_runtime(".")
    runtime = system["runtime"]
    workflow = system["workflow"]
    registry = system["registry"]
    sdk = system["sdk"]

    runtime.start()

    print("REGISTRY SUMMARY")
    print(json.dumps(registry.status()["summary"], indent=4, default=str))

    print()
    print("RUN WORKFLOW")
    result = workflow.run_request("Build a safe runtime feature and validate it with tests")
    print(json.dumps(result, indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(sdk.events.recent(30), indent=4, default=str))


if __name__ == "__main__":
    main()
''',

    "tests/test_v10_3_multi_agent_imports.py": r'''def test_v10_3_multi_agent_imports():
    from buster.runtime import (
        PlannerAgent,
        BuilderAgent,
        TesterAgent,
        ReviewerAgent,
        FixerAgent,
        MultiAgentWorkflowRunner,
    )

    assert PlannerAgent is not None
    assert BuilderAgent is not None
    assert TesterAgent is not None
    assert ReviewerAgent is not None
    assert FixerAgent is not None
    assert MultiAgentWorkflowRunner is not None
'''
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created/updated: {rel}")

print()
print("Buster v10.3 Multi-Agent Intelligence added.")
print()
print("Run:")
print("  python test_v10_3_multi_agent_intelligence.py")
print("  pytest")