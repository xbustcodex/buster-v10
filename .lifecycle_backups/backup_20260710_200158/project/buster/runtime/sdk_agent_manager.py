from __future__ import annotations

from typing import Any, Dict


class SDKAgentManager:
    def __init__(self, sdk):
        self.sdk = sdk
        self.agents: Dict[str, Any] = {}

    def register(self, name: str, agent: Any):
        self.agents[name] = agent
        self.sdk.register_service(f"agent.{name}", agent)
        self.sdk.publish("agent.registered", {"name": name}, source="agent_manager")
        return agent

    def get(self, name: str):
        return self.agents.get(name)

    def require(self, name: str):
        if name not in self.agents:
            raise KeyError(f"Agent not registered: {name}")
        return self.agents[name]

    def run(self, name: str, task=None):
        agent = self.require(name)
        self.sdk.publish("agent.started", {"name": name, "task": task}, source="agent_manager")
        result = agent.run(task)
        self.sdk.publish("agent.finished", {"name": name, "result": result}, source="agent_manager")
        return result

    def names(self):
        return sorted(self.agents.keys())

    def status(self):
        return {
            "count": len(self.agents),
            "agents": self.names(),
        }
