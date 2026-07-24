"""
Sandbox Manager for Buster Kernel v10.5
Manages safe execution environments, isolated task execution, and temporary code evaluation.
"""

from __future__ import annotations

import logging
import sys
import trace
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("buster.kernel.sandbox_manager")


class SandboxExecutionResult:
    """Encapsulates execution output, errors, and metadata from a sandbox run."""

    def __init__(self, success: bool, output: str, error: Optional[str] = None, return_value: Any = None):
        self.success = success
        self.output = output
        self.error = error
        self.return_value = return_value

    def __repr__(self) -> str:
        return f"<SandboxExecutionResult success={self.success} output_len={len(self.output)} error={bool(self.error)}>"


class SandboxManager:
    """Isolated environment manager for safe dynamic python payload execution."""

    def __init__(self, security_intercept=None, workspace_dir: Optional[Path] = None):
        self.security_intercept = security_intercept
        self.workspace_dir = (workspace_dir or Path.cwd() / "sandbox_workspace").resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def execute_code(self, code_content: str, global_vars: Optional[Dict[str, Any]] = None) -> SandboxExecutionResult:
        """Executes raw code in an isolated scope while capturing stdout/stderr."""
        # 1. Security Pre-check
        if self.security_intercept:
            is_safe, warnings = self.security_intercept.inspect_payload(code_content)
            if not is_safe:
                err_msg = f"Sandbox execution blocked by SecurityIntercept: {warnings}"
                logger.error(err_msg)
                return SandboxExecutionResult(success=False, output="", error=err_msg)

        # 2. Setup stdout/stderr redirection
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr

        exec_scope: Dict[str, Any] = global_vars or {}
        exec_scope["__name__"] = "__sandbox__"

        success = False
        error_msg = None
        ret_val = None

        try:
            sys.stdout, sys.stderr = stdout_capture, stderr_capture
            
            # Execute in controlled scope
            compiled_code = compile(code_content, "<sandbox>", "exec")
            ret_val = exec(compiled_code, exec_scope)
            success = True

        except Exception as exc:
            logger.exception("Sandbox execution encountered an unhandled exception")
            error_msg = str(exc)
            success = False

        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        output_log = stdout_capture.getvalue()
        if stderr_capture.getvalue():
            output_log += f"\n[STDERR]\n{stderr_capture.getvalue()}"

        return SandboxExecutionResult(
            success=success,
            output=output_log.strip(),
            error=error_msg,
            return_value=ret_val,
        )