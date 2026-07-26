# buster/capabilities/esp32_cap.py
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


class ESP32Capability(Capability):
    capability_id = "core.esp32"
    name = "ESP32 Microcontroller Capability"
    version = "1.0.0"

    def __init__(self, registry_ref=None) -> None:
        self._registry_ref = registry_ref

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            capability_id=self.capability_id,
            name=self.name,
            version=self.version,
            description="Provides ESP32 serial port discovery and esptool flashing utilities.",
            actions=(
                ActionDescriptor(
                    name="esp32.check_tool",
                    description="Verifies if esptool is available.",
                    input_schema={},
                    output_schema={"available": "bool"},
                    required_permissions=("device.esp32.flash",),
                    risk_level="low",
                ),
            ),
            required_permissions=("device.esp32.flash",),
            resource_requirements=ResourceRequirements(cpu_cores=0.2, memory_mb=64),
            provider="buster",
            tags=("esp32", "hardware", "iot", "firmware"),
            enabled_by_default=True,
        )

    def health_check(self) -> CapabilityHealth:
        start = time.perf_counter()
        try:
            res = subprocess.run(["esptool.py", "version"], capture_output=True, text=True, timeout=5)
            latency = (time.perf_counter() - start) * 1000.0
            return HealthEvaluator.create_health(
                self.capability_id,
                "HEALTHY" if res.returncode == 0 else "DEGRADED",
                latency_ms=latency,
                message="esptool diagnostic completed.",
                diagnostics={"esptool_available": res.returncode == 0},
            )
        except Exception:
            return HealthEvaluator.create_health(self.capability_id, "DEGRADED", message="esptool.py not detected in PATH.", diagnostics={"esptool_available": False})

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
            res = subprocess.run(["esptool.py", "version"], capture_output=True, text=True, timeout=5)
            output = {"available": res.returncode == 0, "output": res.stdout.strip()}
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=False, capability_id=self.capability_id, action=action, error=str(e), duration_ms=duration)