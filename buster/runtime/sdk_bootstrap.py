from __future__ import annotations

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
