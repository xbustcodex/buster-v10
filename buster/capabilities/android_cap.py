# buster/capabilities/android_cap.py
from __future__ import annotations

import time
import subprocess
from typing import Any, Mapping

from buster.capabilities.base import Capability
from buster.capabilities.models import (
    CapabilityDescriptor,
    CapabilityHealth,
    CapabilityExecutionContext,
    CapabilityResult,
    ActionDescriptor,
    ResourceRequirements,
)
from buster.capabilities.permissions import PermissionGate
from buster.capabilities.health import HealthEvaluator
from buster.capabilities.exceptions import ActionNotSupportedError, ActionValidationError, CapabilityDisabledError


class AndroidCapability(Capability):
    capability_id = "core.android"
    name = "Android & Termux Control Capability"
    version = "1.0.0"

    def __init__(self, registry_ref=None) -> None:
        self._registry_ref = registry_ref

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            capability_id=self.capability_id,
            name=self.name,
            version=self.version,
            description="Provides ADB device connection status and Termux command execution.",
            actions=(
                ActionDescriptor(
                    name="android.adb_devices",
                    description="Lists connected ADB devices.",
                    input_schema={},
                    output_schema={"devices": "list[str]"},
                    required_permissions=("device.android.control",),
                    risk_level="low",
                ),
            ),
            required_permissions=("device.android.control",),
            resource_requirements=ResourceRequirements(cpu_cores=0.2, memory_mb=64),
            provider="buster",
            tags=("android", "termux", "adb", "mobile"),
            enabled_by_default=True,
        )

    def health_check(self) -> CapabilityHealth:
        start = time.perf_counter()
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            latency = (time.perf_counter() - start) * 1000.0
            return HealthEvaluator.create_health(
                self.capability_id,
                "HEALTHY" if res.returncode == 0 else "DEGRADED",
                latency_ms=latency,
                message="ADB diagnostic completed.",
                diagnostics={"adb_available": res.returncode == 0},
            )
        except Exception as e:
            return HealthEvaluator.create_health(self.capability_id, "UNAVAILABLE", message=str(e), diagnostics={"adb_available": False})

    def execute(
        self,
        action: str,
        arguments: Mapping[str, Any],
        context: CapabilityExecutionContext,
    ) -> CapabilityResult:
        start_time = time.perf_counter()
        desc = self.describe()

        if self._registry_ref and not self._registry_ref.is_enabled(self.capability_id):
            raise CapabilityDisabledError(f"Capability '{self.capability_id}' is disabled.")

        action_desc = next((a for a in desc.actions if a.name == action), None)
        if not action_desc:
            raise ActionNotSupportedError(f"Action '{action}' not supported.")

        PermissionGate.verify_permissions(desc, action_desc, context)

        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True, timeout=5)
            devices = [line.split()[0] for line in res.stdout.strip().splitlines()[1:] if line.strip()]
            output = {"devices": devices}
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=False, capability_id=self.capability_id, action=action, error=str(e), duration_ms=duration)