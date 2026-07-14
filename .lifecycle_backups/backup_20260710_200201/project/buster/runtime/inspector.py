from __future__ import annotations

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
