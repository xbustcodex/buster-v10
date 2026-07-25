from __future__ import annotations

from enum import Enum, auto
from typing import Dict, Any


class Capability(Enum):
    READ_FILES = "READ_FILES"
    WRITE_FILES = "WRITE_FILES"
    DELETE_FILES = "DELETE_FILES"
    GIT_COMMIT = "GIT_COMMIT"
    GIT_PUSH = "GIT_PUSH"
    DESKTOP_CONTROL = "DESKTOP_CONTROL"
    BROWSER_CONTROL = "BROWSER_CONTROL"
    POWER_ACTIONS = "POWER_ACTIONS"
    NETWORK = "NETWORK"
    EMAIL = "EMAIL"
    PLUGIN_INSTALL = "PLUGIN_INSTALL"


class ExecutionPermission(Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    PROMPT_USER = "PROMPT_USER"
    ALWAYS_ASK = "ALWAYS_ASK"
    DENY = "DENY"


class CapabilityPolicy:
    """Defines permission rules for system capabilities."""

    DEFAULT_MATRIX: Dict[Capability, ExecutionPermission] = {
        Capability.READ_FILES: ExecutionPermission.AUTO_APPROVE,
        Capability.WRITE_FILES: ExecutionPermission.PROMPT_USER,
        Capability.DELETE_FILES: ExecutionPermission.ALWAYS_ASK,
        Capability.GIT_COMMIT: ExecutionPermission.AUTO_APPROVE,
        Capability.GIT_PUSH: ExecutionPermission.PROMPT_USER,
        Capability.DESKTOP_CONTROL: ExecutionPermission.PROMPT_USER,
        Capability.BROWSER_CONTROL: ExecutionPermission.PROMPT_USER,
        Capability.POWER_ACTIONS: ExecutionPermission.ALWAYS_ASK,
        Capability.NETWORK: ExecutionPermission.PROMPT_USER,
        Capability.EMAIL: ExecutionPermission.ALWAYS_ASK,
        Capability.PLUGIN_INSTALL: ExecutionPermission.ALWAYS_ASK,
    }

    def __init__(self, custom_matrix: Dict[Capability, ExecutionPermission] | None = None):
        self.matrix = dict(self.DEFAULT_MATRIX)
        if custom_matrix:
            self.matrix.update(custom_matrix)

    def get_permission(self, capability: Capability) -> ExecutionPermission:
        return self.matrix.get(capability, ExecutionPermission.ALWAYS_ASK)

    def is_auto_approved(self, capability: Capability) -> bool:
        return self.get_permission(capability) == ExecutionPermission.AUTO_APPROVE