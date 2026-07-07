from __future__ import annotations

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
