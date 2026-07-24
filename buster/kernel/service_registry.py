"""
Service Registry for Buster Kernel v10.5
Provides dynamic registration, lifecycle tracking, and dependency resolution for kernel services.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type, TypeVar

logger = logging.getLogger("buster.kernel.service_registry")

T = TypeVar("T")


class ServiceRegistry:
    """Central registry for managing component instances and dependencies."""

    _instance: Optional[ServiceRegistry] = None

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def instance(cls) -> ServiceRegistry:
        """Singleton instance accessor."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, name: str, service_instance: Any, version: str = "1.0.0") -> None:
        """Register a active service instance with optional metadata."""
        if name in self._services:
            logger.warning(f"Overwriting existing service registration: '{name}'")
        
        self._services[name] = service_instance
        self._metadata[name] = {
            "version": version,
            "type": type(service_instance).__name__,
        }
        logger.info(f"Registered service: {name} (v{version})")

    def get(self, name: str) -> Optional[Any]:
        """Retrieve a registered service by name."""
        service = self._services.get(name)
        if service is None:
            logger.debug(f"Service requested but not found: '{name}'")
        return service

    def require(self, name: str) -> Any:
        """Retrieve a service or raise KeyError if missing."""
        service = self.get(name)
        if service is None:
            raise KeyError(f"Required kernel service '{name}' is not registered!")
        return service

    def unregister(self, name: str) -> bool:
        """Unregister a service from the registry."""
        if name in self._services:
            del self._services[name]
            del self._metadata[name]
            logger.info(f"Unregistered service: {name}")
            return True
        return False

    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """List all registered services and their metadata."""
        return {
            name: {**meta, "active": True}
            for name, meta in self._metadata.items()
        }