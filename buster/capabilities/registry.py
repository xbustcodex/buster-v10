# buster/capabilities/registry.py
from __future__ import annotations

import logging
import threading
from typing import Dict, Tuple, Optional

from buster.capabilities.base import Capability
from buster.capabilities.models import CapabilityDescriptor, CapabilityHealth, ActionDescriptor
from buster.capabilities.exceptions import (
    CapabilityNotFoundError,
    DuplicateCapabilityError,
    InvalidCapabilityDescriptorError,
)

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Thread-safe discovery and lookup registry for all Buster capabilities."""

    def __init__(self, event_bus=None) -> None:
        self._capabilities: Dict[str, Capability] = {}
        self._descriptors: Dict[str, CapabilityDescriptor] = {}
        self._enabled_states: Dict[str, bool] = {}
        self._lock = threading.RLock()
        self._event_bus = event_bus

    def register(self, capability: Capability) -> None:
        with self._lock:
            desc = capability.describe()
            if not desc or not desc.capability_id:
                raise InvalidCapabilityDescriptorError("Capability descriptor is missing or invalid.")
            
            cap_id = desc.capability_id
            if cap_id in self._capabilities:
                raise DuplicateCapabilityError(f"Capability '{cap_id}' is already registered.")

            # Validate actions
            for action in desc.actions:
                if not action.name:
                    raise InvalidCapabilityDescriptorError(f"Action in capability '{cap_id}' has no name.")

            self._capabilities[cap_id] = capability
            self._descriptors[cap_id] = desc
            self._enabled_states[cap_id] = desc.enabled_by_default

            logger.info(f"Registered capability [{cap_id}] version [{desc.version}]")
            if self._event_bus:
                self._event_bus.publish("capability.registered", {"capability_id": cap_id, "version": desc.version})

    def unregister(self, capability_id: str) -> None:
        with self._lock:
            if capability_id not in self._capabilities:
                raise CapabilityNotFoundError(f"Capability '{capability_id}' not found.")
            
            del self._capabilities[capability_id]
            del self._descriptors[capability_id]
            self._enabled_states.pop(capability_id, None)

            logger.info(f"Unregistered capability [{capability_id}]")
            if self._event_bus:
                self._event_bus.publish("capability.unregistered", {"capability_id": capability_id})

    def get(self, capability_id: str) -> Capability:
        with self._lock:
            if capability_id not in self._capabilities:
                raise CapabilityNotFoundError(f"Capability '{capability_id}' not found.")
            return self._capabilities[capability_id]

    def is_enabled(self, capability_id: str) -> bool:
        with self._lock:
            return self._enabled_states.get(capability_id, False)

    def set_enabled(self, capability_id: str, enabled: bool) -> None:
        with self._lock:
            if capability_id not in self._capabilities:
                raise CapabilityNotFoundError(f"Capability '{capability_id}' not found.")
            self._enabled_states[capability_id] = enabled
            event_name = "capability.enabled" if enabled else "capability.disabled"
            if self._event_bus:
                self._event_bus.publish(event_name, {"capability_id": capability_id})

    def find_by_action(self, action_name: str) -> Tuple[Capability, ...]:
        with self._lock:
            results = []
            for cap_id, desc in sorted(self._descriptors.items()):
                if self._enabled_states.get(cap_id, False):
                    if any(act.name == action_name for act in desc.actions):
                        results.append(self._capabilities[cap_id])
            return tuple(results)

    def list_descriptors(self) -> Tuple[CapabilityDescriptor, ...]:
        with self._lock:
            sorted_ids = sorted(self._descriptors.keys())
            return tuple(self._descriptors[cid] for cid in sorted_ids)

    def health_snapshot(self) -> Tuple[CapabilityHealth, ...]:
        with self._lock:
            snapshots = []
            for cap_id in sorted(self._capabilities.keys()):
                cap = self._capabilities[cap_id]
                if not self._enabled_states.get(cap_id, False):
                    from buster.capabilities.health import HealthEvaluator
                    snapshots.append(HealthEvaluator.create_health(cap_id, "DISABLED", message="Capability is disabled."))
                    continue
                try:
                    health = cap.health_check()
                    snapshots.append(health)
                except Exception as e:
                    from buster.capabilities.health import HealthEvaluator
                    snapshots.append(HealthEvaluator.create_health(cap_id, "UNAVAILABLE", message=str(e)))
            return tuple(snapshots)