"""
Kernel Engine Orchestrator for Buster Kernel v10.5
Initializes and binds the core kernel services (Event Bus, Service Registry, Action Router, 
Security Intercept, and Sandbox Manager) into a unified runtime context.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from buster.kernel.action_router import ActionRouter
from buster.kernel.event_bus import EventBus
from buster.kernel.sandbox_manager import SandboxManager
from buster.kernel.security_intercept import SecurityIntercept
from buster.kernel.service_registry import ServiceRegistry

logger = logging.getLogger("buster.kernel.kernel_engine")


class KernelEngine:
    """Master Kernel Engine orchestrating core services and lifecycle event loops."""

    def __init__(self):
        self.registry = ServiceRegistry.instance()
        self.event_bus = EventBus()
        self.security = SecurityIntercept()
        self.sandbox = SandboxManager(security_intercept=self.security)
        self.router = ActionRouter(event_bus=self.event_bus, service_registry=self.registry)

        self._bootstrapped = False

    def bootstrap(self) -> None:
        """Initializes and registers core kernel components."""
        if self._bootstrapped:
            logger.warning("Kernel Engine already bootstrapped.")
            return

        logger.info("Bootstrapping Buster Kernel v10.5...")

        # Register foundational services
        self.registry.register("event_bus", self.event_bus, version="10.5.0")
        self.registry.register("security_intercept", self.security, version="10.5.0")
        self.registry.register("sandbox_manager", self.sandbox, version="10.5.0")
        self.registry.register("action_router", self.router, version="10.5.0")
        self.registry.register("kernel_engine", self, version="10.5.0")

        # Broadcast kernel boot event
        self.event_bus.publish("kernel:bootstrapped", {"status": "ready", "version": "10.5.0"})
        self._bootstrapped = True
        logger.info("Buster Kernel v10.5 successfully bootstrapped.")

    def get_status(self) -> Dict[str, Any]:
        """Returns the active state of all core kernel modules."""
        return {
            "bootstrapped": self._bootstrapped,
            "registered_services": self.registry.list_services(),
            "recent_events": len(self.event_bus.get_history()),
            "actions_available": self.router.list_actions(),
        }