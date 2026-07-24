"""
Buster Kernel - Capability & RBAC Permission Engine
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger("BusterKernel.Permissions")


class PermissionScope(Enum):
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    TERMINAL_EXEC = "terminal:exec"
    GIT_COMMIT = "git:commit"
    SYSTEM_SHUTDOWN = "system:shutdown"
    SECRET_READ = "secret:read"
    SYSTEM_MODIFY = "system:modify"


class PermissionManager:
    """Enforces capability-based security policies for registered agents."""

    def __init__(self) -> None:
        # Default Scope Matrix
        self._role_permissions: Dict[str, Set[PermissionScope]] = {
            "admin": set(PermissionScope),
            "builder": {
                PermissionScope.FILE_READ,
                PermissionScope.FILE_WRITE,
                PermissionScope.TERMINAL_EXEC,
                PermissionScope.GIT_COMMIT,
            },
            "researcher": {
                PermissionScope.FILE_READ,
            },
            "tester": {
                PermissionScope.FILE_READ,
                PermissionScope.TERMINAL_EXEC,
            },
        }
        self._agent_roles: Dict[str, str] = {}

    def assign_role(self, agent_id: str, role: str) -> None:
        """Binds an agent instance to a specific security role."""
        if role not in self._role_permissions:
            raise ValueError(f"Unknown role: {role}")
        self._agent_roles[agent_id] = role
        logger.info(f"Assigned role '{role}' to agent '{agent_id}'")

    def authorize(self, agent_id: str, scope: PermissionScope) -> bool:
        """Verifies if an agent holds the requested permission scope."""
        role = self._agent_roles.get(agent_id)
        if not role:
            logger.warning(f"Access Denied: Agent '{agent_id}' has no assigned role.")
            return False

        allowed_scopes = self._role_permissions.get(role, set())
        if scope in allowed_scopes:
            return True

        logger.warning(f"Access Denied: Agent '{agent_id}' [{role}] attempted unauthorized action '{scope.value}'")
        return False