from __future__ import annotations

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
