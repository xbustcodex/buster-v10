# buster/capabilities/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from buster.capabilities.models import (
        CapabilityDescriptor,
        CapabilityHealth,
        CapabilityExecutionContext,
        CapabilityResult,
    )


class Capability(ABC):
    capability_id: str
    name: str
    version: str

    @abstractmethod
    def describe(self) -> CapabilityDescriptor:
        """Return schema, permissions, actions, resources, and metadata."""

    @abstractmethod
    def health_check(self) -> CapabilityHealth:
        """Return current readiness and diagnostic details."""

    @abstractmethod
    def execute(
        self,
        action: str,
        arguments: Mapping[str, Any],
        context: CapabilityExecutionContext,
    ) -> CapabilityResult:
        """Execute one declared action."""