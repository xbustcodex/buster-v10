# buster/capabilities/permissions.py
from __future__ import annotations

import logging
from typing import Iterable, Set

from buster.capabilities.exceptions import PermissionDeniedError
from buster.capabilities.models import ActionDescriptor, CapabilityDescriptor, CapabilityExecutionContext

logger = logging.getLogger(__name__)


class PermissionGate:
    """Enforces fine-grained permission evaluation per capability action."""

    @staticmethod
    def verify_permissions(
        capability: CapabilityDescriptor,
        action: ActionDescriptor,
        context: CapabilityExecutionContext,
    ) -> None:
        """Validates that all required permissions for the capability and action are present in context."""
        required: Set[str] = set(capability.required_permissions).union(action.required_permissions)
        approved: Set[str] = set(context.approved_permissions)

        missing = required - approved
        if missing:
            logger.warning(
                f"Permission denied for mission [{context.mission_id}], task [{context.task_id}], "
                f"trace [{context.trace_id}]. Missing permissions: {missing}"
            )
            raise PermissionDeniedError(
                f"Action '{action.name}' on capability '{capability.capability_id}' requires permissions: {sorted(list(missing))}"
            )