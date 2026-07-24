"""
Buster Kernel - Transient Agent Registry
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger("BusterKernel.AgentManager")


class AgentState(Enum):
    IDLE = auto()
    WORKING = auto()
    PAUSED = auto()
    TERMINATED = auto()


@dataclass
class AgentDescriptor:
    agent_id: str
    agent_type: str  # e.g. "BuilderAgent", "TesterAgent"
    instance: Any
    role: str
    state: AgentState = AgentState.IDLE


class AgentManager:
    """Manages execution lifecycles and registration for transient worker agents."""

    def __init__(self, permissions_mgr=None) -> None:
        self.agents: Dict[str, AgentDescriptor] = {}
        self.permissions_mgr = permissions_mgr

    def register_agent(self, agent_id: str, agent_type: str, instance: Any, role: str) -> None:
        """Registers an agent instance and hooks it to permissions."""
        self.agents[agent_id] = AgentDescriptor(
            agent_id=agent_id,
            agent_type=agent_type,
            instance=instance,
            role=role,
        )
        if self.permissions_mgr:
            self.permissions_mgr.assign_role(agent_id, role)
        logger.info(f"Registered Agent '{agent_id}' ({agent_type}) bound to role '{role}'")

    def get_agent(self, agent_id: str) -> Optional[AgentDescriptor]:
        return self.agents.get(agent_id)