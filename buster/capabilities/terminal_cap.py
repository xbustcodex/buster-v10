# buster/capabilities/terminal_cap.py
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


class TerminalCapability(Capability):
    capability_id = "core.terminal"
    name = "Terminal Shell Capability"
    version = "1.0.0"

    def __init__(self, registry_ref=None) -> None:
        self._registry_ref = registry_ref

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            capability_id=self.capability_id,
            name=self.name,
            version=self.version,
            description="Executes shell commands and scripts in a controlled environment.",
            actions=(
                ActionDescriptor(
                    name="terminal.execute",
                    description="Executes a shell command and returns output.",
                    input_schema={"command": "str", "cwd": "str | None"},
                    output_schema={"exit_code": "int", "stdout": "str", "stderr": "str"},
                    required_permissions=("terminal.execute",),
                    risk_level="high",
                ),
            ),
            required_permissions=("terminal.execute",),
            resource_requirements=ResourceRequirements(cpu_cores=1.0, memory_mb=256, requires_filesystem=True),
            provider="buster",
            tags=("terminal", "shell", "execution"),
            enabled_by_default=True,
        )

    def health_check(self) -> CapabilityHealth:
        start = time.perf_counter()
        try:
            res = subprocess.run(["echo", "buster_ok"], capture_output=True, text=True, timeout=3)
            latency = (time.perf_counter() - start) * 1000.0
            return HealthEvaluator.create_health(
                self.capability_id,
                "HEALTHY",
                latency_ms=latency,
                message="Terminal execution ready.",
                diagnostics={"shell_available": res.returncode == 0},
            )
        except Exception as e:
            return HealthEvaluator.create_health(self.capability_id, "UNAVAILABLE", message=str(e))

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

        command = arguments.get("command")
        if not command:
            raise ActionValidationError("Argument 'command' is required.")
        cwd = arguments.get("cwd")

        try:
            res = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd, timeout=context.timeout_seconds or 30.0)
            output = {"exit_code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=res.returncode == 0, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=False, capability_id=self.capability_id, action=action, error=str(e), duration_ms=duration)