# buster/capabilities/python_cap.py
from __future__ import annotations

import time
import subprocess
import sys
import ast
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


class PythonCapability(Capability):
    capability_id = "core.python"
    name = "Python Environment Capability"
    version = "1.0.0"

    def __init__(self, registry_ref=None) -> None:
        self._registry_ref = registry_ref

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            capability_id=self.capability_id,
            name=self.name,
            version=self.version,
            description="Provides Python version inspection, syntax validation, and test execution.",
            actions=(
                ActionDescriptor(
                    name="python.version",
                    description="Returns the active Python interpreter version.",
                    input_schema={},
                    output_schema={"version": "str", "executable": "str"},
                    required_permissions=(),
                    risk_level="low",
                ),
                ActionDescriptor(
                    name="python.syntax_check",
                    description="Validates Python code syntax without executing it.",
                    input_schema={"code": "str"},
                    output_schema={"valid": "bool", "error": "str | None"},
                    required_permissions=(),
                    risk_level="low",
                ),
                ActionDescriptor(
                    name="python.run_tests",
                    description="Executes a test file or pytest suite.",
                    input_schema={"target": "str"},
                    output_schema={"exit_code": "int", "stdout": "str", "stderr": "str"},
                    required_permissions=("process.launch", "filesystem.read"),
                    risk_level="medium",
                ),
            ),
            required_permissions=("process.launch",),
            resource_requirements=ResourceRequirements(cpu_cores=0.5, memory_mb=128, requires_filesystem=True),
            provider="buster",
            tags=("python", "runtime", "testing"),
            enabled_by_default=True,
        )

    def health_check(self) -> CapabilityHealth:
        start = time.perf_counter()
        try:
            py_ver = sys.version
            latency = (time.perf_counter() - start) * 1000.0
            return HealthEvaluator.create_health(
                self.capability_id,
                "HEALTHY",
                latency_ms=latency,
                message="Python runtime accessible.",
                diagnostics={"executable_found": True, "version_detected": sys.version.split()[0], "executable_path": sys.executable},
            )
        except Exception as e:
            return HealthEvaluator.create_health(self.capability_id, "UNAVAILABLE", message=str(e), diagnostics={"executable_found": False})

    def execute(
        self,
        action: str,
        arguments: Mapping[str, Any],
        context: CapabilityExecutionContext,
    ) -> CapabilityResult:
        start_time = time.perf_counter()
        desc = self.describe()

        # Check if enabled via registry if available
        if self._registry_ref and not self._registry_ref.is_enabled(self.capability_id):
            raise CapabilityDisabledError(f"Capability '{self.capability_id}' is currently disabled.")

        # Resolve action descriptor
        action_desc = next((a for a in desc.actions if a.name == action), None)
        if not action_desc:
            raise ActionNotSupportedError(f"Action '{action}' not supported by capability '{self.capability_id}'.")

        # Enforce Permissions
        PermissionGate.verify_permissions(desc, action_desc, context)

        try:
            if action == "python.version":
                output = {"version": sys.version, "executable": sys.executable}
                duration = (time.perf_counter() - start_time) * 1000.0
                return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)

            elif action == "python.syntax_check":
                code = arguments.get("code")
                if not isinstance(code, str):
                    raise ActionValidationError("Argument 'code' must be a string.")
                try:
                    ast.parse(code)
                    output = {"valid": True, "error": None}
                except SyntaxError as se:
                    output = {"valid": False, "error": str(se)}
                duration = (time.perf_counter() - start_time) * 1000.0
                return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)

            elif action == "python.run_tests":
                target = arguments.get("target", "tests")
                cmd = [sys.executable, "-m", "pytest", target]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=context.timeout_seconds or 30.0)
                output = {"exit_code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
                duration = (time.perf_counter() - start_time) * 1000.0
                return CapabilityResult(
                    success=res.returncode == 0,
                    capability_id=self.capability_id,
                    action=action,
                    output=output,
                    duration_ms=duration,
                )

            else:
                raise ActionNotSupportedError(f"Action '{action}' is not implemented.")

        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=False, capability_id=self.capability_id, action=action, error=str(e), duration_ms=duration)