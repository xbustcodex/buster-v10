# buster/capabilities/filesystem_cap.py
from __future__ import annotations

import time
from pathlib import Path
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


class FilesystemCapability(Capability):
    capability_id = "core.filesystem"
    name = "Filesystem Capability"
    version = "1.0.0"

    def __init__(self, registry_ref=None) -> None:
        self._registry_ref = registry_ref

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            capability_id=self.capability_id,
            name=self.name,
            version=self.version,
            description="Provides secure file reading, writing, and directory listing within the workspace.",
            actions=(
                ActionDescriptor(
                    name="filesystem.read_file",
                    description="Reads text content from a file path.",
                    input_schema={"file_path": "str"},
                    output_schema={"content": "str"},
                    required_permissions=("filesystem.read",),
                    risk_level="low",
                ),
                ActionDescriptor(
                    name="filesystem.write_file",
                    description="Writes text content to a file path.",
                    input_schema={"file_path": "str", "content": "str"},
                    output_schema={"bytes_written": "int"},
                    required_permissions=("filesystem.write",),
                    risk_level="medium",
                    reversible=True,
                ),
            ),
            required_permissions=("filesystem.read",),
            resource_requirements=ResourceRequirements(cpu_cores=0.1, memory_mb=32, requires_filesystem=True),
            provider="buster",
            tags=("filesystem", "io", "storage"),
            enabled_by_default=True,
        )

    def health_check(self) -> CapabilityHealth:
        start = time.perf_counter()
        try:
            cwd = Path.cwd()
            latency = (time.perf_counter() - start) * 1000.0
            return HealthEvaluator.create_health(
                self.capability_id,
                "HEALTHY",
                latency_ms=latency,
                message="Filesystem accessible.",
                diagnostics={"cwd": str(cwd), "writable": cwd.stat() is not None},
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
            raise CapabilityDisabledError(f"Capability '{self.capability_id}' is currently disabled.")

        action_desc = next((a for a in desc.actions if a.name == action), None)
        if not action_desc:
            raise ActionNotSupportedError(f"Action '{action}' not supported by capability '{self.capability_id}'.")

        PermissionGate.verify_permissions(desc, action_desc, context)

        file_path_str = arguments.get("file_path")
        if not file_path_str:
            raise ActionValidationError("Argument 'file_path' is required.")

        target_path = Path(file_path_str)

        try:
            if action == "filesystem.read_file":
                content = target_path.read_text(encoding="utf-8")
                output = {"content": content}
                duration = (time.perf_counter() - start_time) * 1000.0
                return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)

            elif action == "filesystem.write_file":
                content = arguments.get("content", "")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                bytes_written = len(content.encode("utf-8"))
                output = {"bytes_written": bytes_written}
                duration = (time.perf_counter() - start_time) * 1000.0
                return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)

            else:
                raise ActionNotSupportedError(f"Action '{action}' is not implemented.")

        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=False, capability_id=self.capability_id, action=action, error=str(e), duration_ms=duration)