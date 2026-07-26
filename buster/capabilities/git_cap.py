# buster/capabilities/git_cap.py
from __future__ import annotations

import time
import subprocess
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


class GitCapability(Capability):
    capability_id = "core.git"
    name = "Git Version Control Capability"
    version = "1.0.0"

    def __init__(self, registry_ref=None) -> None:
        self._registry_ref = registry_ref

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            capability_id=self.capability_id,
            name=self.name,
            version=self.version,
            description="Provides repository status inspection, staging, committing, and branching.",
            actions=(
                ActionDescriptor(
                    name="git.status",
                    description="Returns the current git status of the repository workspace.",
                    input_schema={"repo_path": "str"},
                    output_schema={"clean": "bool", "status_output": "str"},
                    required_permissions=("git.read",),
                    risk_level="low",
                ),
                ActionDescriptor(
                    name="git.commit",
                    description="Stages changes and commits with a message.",
                    input_schema={"repo_path": "str", "message": "str", "files": "list[str]"},
                    output_schema={"commit_hash": "str"},
                    required_permissions=("git.read", "git.commit", "filesystem.write"),
                    risk_level="medium",
                ),
            ),
            required_permissions=("git.read",),
            resource_requirements=ResourceRequirements(cpu_cores=0.2, memory_mb=64, requires_filesystem=True),
            provider="buster",
            tags=("git", "version-control", "scm"),
            enabled_by_default=True,
        )

    def health_check(self) -> CapabilityHealth:
        start = time.perf_counter()
        try:
            res = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            latency = (time.perf_counter() - start) * 1000.0
            if res.returncode == 0:
                version_str = res.stdout.strip()
                return HealthEvaluator.create_health(
                    self.capability_id,
                    "HEALTHY",
                    latency_ms=latency,
                    message="Git executable available.",
                    diagnostics={"executable_found": True, "git_version": version_str},
                )
            else:
                return HealthEvaluator.create_health(self.capability_id, "DEGRADED", message="Git command returned non-zero exit code.")
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

        if self._registry_ref and not self._registry_ref.is_enabled(self.capability_id):
            raise CapabilityDisabledError(f"Capability '{self.capability_id}' is currently disabled.")

        action_desc = next((a for a in desc.actions if a.name == action), None)
        if not action_desc:
            raise ActionNotSupportedError(f"Action '{action}' not supported by capability '{self.capability_id}'.")

        PermissionGate.verify_permissions(desc, action_desc, context)

        repo_path = arguments.get("repo_path", ".")

        try:
            if action == "git.status":
                res = subprocess.run(["git", "-C", repo_path, "status", "--porcelain"], capture_output=True, text=True, check=True)
                clean = len(res.stdout.strip()) == 0
                output = {"clean": clean, "status_output": res.stdout}
                duration = (time.perf_counter() - start_time) * 1000.0
                return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)

            elif action == "git.commit":
                message = arguments.get("message")
                files = arguments.get("files", ["."])
                if not message:
                    raise ActionValidationError("Commit message is required.")
                
                # Stage files
                subprocess.run(["git", "-C", repo_path, "add"] + files, check=True)
                # Commit
                commit_res = subprocess.run(["git", "-C", repo_path, "commit", "-m", message], capture_output=True, text=True, check=True)
                
                output = {"commit_hash": commit_res.stdout[:50]}
                duration = (time.perf_counter() - start_time) * 1000.0
                return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)

            else:
                raise ActionNotSupportedError(f"Action '{action}' is not implemented.")

        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=False, capability_id=self.capability_id, action=action, error=str(e), duration_ms=duration)