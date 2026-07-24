"""
Buster Kernel - Core Micro-Kernel Architecture

Serves as the central runtime coordinator managing process lifecycle,
thread-safe state memory, and pub/sub IPC event routing via the Trie EventRouter.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import logging

from buster.kernel.event_router import EventRouter, EventPriority

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BusterKernel")


class KernelState(Enum):
    OFFLINE = auto()
    BOOTING = auto()
    READY = auto()
    DEGRADED = auto()
    SHUTTING_DOWN = auto()


@dataclass
class ServiceDescriptor:
    name: str
    instance: Any
    priority: int = 100
    is_critical: bool = False
    status: str = "INITIALIZED"


class BusterKernel:
    """Central Micro-Kernel Engine for Buster OS / Runtime."""

    _instance: Optional[BusterKernel] = None

    def __new__(cls) -> BusterKernel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.state = KernelState.OFFLINE
        self.services: Dict[str, ServiceDescriptor] = {}
        self.router = EventRouter(max_workers=8)
        self.memory_store: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="buster_kernel_worker")
        self._initialized = True
        logger.info("Buster Kernel initialized.")

    # ------------------------------------------------------------------
    # Lifecycle Management
    # ------------------------------------------------------------------
    def boot(self) -> bool:
        """Boots the kernel and starts all registered services."""
        self.state = KernelState.BOOTING
        logger.info("Booting Buster Kernel...")

        try:
            # Sort by priority (lower number = higher priority)
            sorted_services = sorted(self.services.values(), key=lambda s: s.priority)

            for desc in sorted_services:
                if hasattr(desc.instance, "start"):
                    desc.instance.start()
                desc.status = "ACTIVE"
                logger.info(f"Service loaded: {desc.name}")

            self.state = KernelState.READY
            self.publish("buster.kernel.state.changed", {"state": self.state.name}, priority=EventPriority.CRITICAL)
            logger.info("Buster Kernel booted successfully. State: READY")
            return True

        except Exception as err:
            self.state = KernelState.DEGRADED
            logger.error(f"Kernel Boot Failure: {err}")
            return False

    def shutdown(self) -> None:
        """Gracefully terminates services, event router, and thread pool."""
        self.state = KernelState.SHUTTING_DOWN
        logger.info("Kernel shutting down...")

        for desc in self.services.values():
            if hasattr(desc.instance, "stop"):
                try:
                    desc.instance.stop()
                except Exception as e:
                    logger.warning(f"Error stopping service {desc.name}: {e}")
            desc.status = "STOPPED"

        # Drain event router thread pool
        self.router.shutdown()

        self.executor.shutdown(wait=False)
        self.state = KernelState.OFFLINE
        logger.info("Kernel offline.")

    # ------------------------------------------------------------------
    # Service Registry
    # ------------------------------------------------------------------
    def register_service(self, name: str, instance: Any, priority: int = 100, is_critical: bool = False) -> None:
        """Registers a subsystem or service into the kernel."""
        self.services[name] = ServiceDescriptor(
            name=name,
            instance=instance,
            priority=priority,
            is_critical=is_critical
        )
        logger.info(f"Registered service '{name}' [Priority: {priority}]")

    def get_service(self, name: str) -> Optional[Any]:
        desc = self.services.get(name)
        return desc.instance if desc else None

    # ------------------------------------------------------------------
    # IPC Event Bus
    # ------------------------------------------------------------------
    def subscribe(self, pattern: str, callback: Callable[[Any], None], subscriber_id: str = "anonymous") -> None:
        """Subscribes a listener callback to a topic pattern via Trie EventRouter."""
        self.router.subscribe(pattern=pattern, callback=callback, subscriber_id=subscriber_id)

    def publish(
        self, 
        topic: str, 
        payload: Any = None, 
        priority: EventPriority = EventPriority.NORMAL
    ) -> None:
        """Publishes an event asynchronously across subscribers using the Trie EventRouter."""
        payload_dict = payload if isinstance(payload, dict) else {"data": payload}
        self.router.publish(topic=topic, payload=payload_dict, source="kernel", priority=priority)

    # ------------------------------------------------------------------
    # Shared State Store
    # ------------------------------------------------------------------
    def set_state(self, key: str, value: Any) -> None:
        self.memory_store[key] = value
        self.publish(f"buster.state.{key}", value)

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.memory_store.get(key, default)