from __future__ import annotations

from typing import Dict, Iterable

from .agent_service import AgentService


class AgentRegistry:
    def __init__(self) -> None:
        self.agents: Dict[str, AgentService] = {}

    def register(self, agent: AgentService) -> AgentService:
        self.agents[agent.name] = agent
        return agent

    def get(self, name: str) -> AgentService | None:
        return self.agents.get(name)

    def require(self, name: str) -> AgentService:
        if name not in self.agents:
            raise KeyError(f"Missing agent: {name}")
        return self.agents[name]

    def all(self) -> Iterable[AgentService]:
        return self.agents.values()

    def status(self) -> dict:
        return {
            "count": len(self.agents),
            "agents": {name: agent.status() for name, agent in self.agents.items()},
        }
