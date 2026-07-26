# buster/capabilities/windows_cap.py
from __future__ import annotations

import time
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


class WindowsAutomationCapability(Capability):
    capability_id = "core.windows"
    name = "Windows Automation Capability"
    version = "1.0.0"

    def __init__(self, registry_ref=None) -> None:
        self._registry_ref = registry_ref

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            capability_id=self.capability_id,
            name=self.name,
            version=self.version,
            description="Provides desktop window management and UI automation on Windows.",
            actions=(
                ActionDescriptor(
                    name="windows.list_windows",
                    description="Lists active visible top-level windows.",
                    input_schema={},
                    output_schema={"windows": "list[str]"},
                    required_permissions=("process.launch",),
                    risk_level="low",
                ),
            ),
            required_permissions=("process.launch",),
            resource_requirements=ResourceRequirements(cpu_cores=0.2, memory_mb=64),
            provider="buster",
            tags=("windows", "ui", "desktop"),
            enabled_by_default=True,
        )

    def health_check(self) -> CapabilityHealth:
        start = time.perf_counter()
        import sys
        latency = (time.perf_counter() - start) * 1000.0
        is_windows = sys.platform == "win32"
        status = "HEALTHY" if is_windows else "DEGRADED"
        msg = "Windows OS detected." if is_windows else "Non-Windows environment."
        return HealthEvaluator.create_health(self.capability_id, status, latency_ms=latency, message=msg, diagnostics={"win32": is_windows})

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
            import sys
            if sys.platform != "win32":
                raise RuntimeError("Windows automation is only supported on Windows hosts.")

            import ctypes
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
            GetWindowTextW = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
            IsWindowVisible = ctypes.windll.user32.IsWindowVisible

            titles = []
            def foreach_window(hwnd, lParam):
                if IsWindowVisible(hwnd):
                    length = GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        GetWindowTextW(hwnd, buff, length + 1)
                        titles.append(buff.value)
                return True

            EnumWindows(EnumWindowsProc(foreach_window), 0)

            output = {"windows": titles[:50]}
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=False, capability_id=self.capability_id, action=action, error=str(e), duration_ms=duration)