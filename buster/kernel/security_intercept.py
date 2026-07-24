"""
Security Intercept Guardrail for Buster Kernel v10.5
Provides safety checks, path traversal protection, and payload inspection before execution.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("buster.kernel.security_intercept")


class SecurityIntercept:
    """Kernel guardrail enforcing system boundary security and payload safety."""

    # Patterns considered restricted or potentially hazardous
    BLOCKED_PATTERNS = [
        re.compile(r"import\s+os\s*;\s*os\.system", re.IGNORECASE),
        re.compile(r"subprocess\.\w*Popen", re.IGNORECASE),
        re.compile(r"eval\(", re.IGNORECASE),
        re.compile(r"exec\(", re.IGNORECASE),
        re.compile(r"__import__\(", re.IGNORECASE),
    ]

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = (project_root or Path.cwd()).resolve()
        self._strict_mode: bool = True

    def validate_path(self, target_path: str | Path) -> Tuple[bool, str]:
        """Ensures file targets stay within permitted workspace boundaries."""
        try:
            resolved_path = (self.project_root / target_path).resolve()
            if not str(resolved_path).startswith(str(self.project_root)):
                return False, f"Path traversal attempt blocked: '{target_path}'"
            return True, "Path validated"
        except Exception as exc:
            return False, f"Invalid path structure: {exc}"

    def inspect_payload(self, code_content: str) -> Tuple[bool, List[str]]:
        """Scans code payloads for unsafe patterns prior to hot-execution."""
        warnings: List[str] = []
        
        for pattern in self.BLOCKED_PATTERNS:
            if pattern.search(code_content):
                warnings.append(f"Security Alert: Suspicious pattern matched '{pattern.pattern}'")

        if warnings and self._strict_mode:
            logger.warning(f"Payload inspection flagged {len(warnings)} issue(s).")
            return False, warnings

        return True, warnings

    def authorize_action(self, action_type: str, payload: Dict[str, Any]) -> bool:
        """Determines if a given action is allowed to execute."""
        # Check target files if specified in payload
        if "file_path" in payload:
            valid, msg = self.validate_path(payload["file_path"])
            if not valid:
                logger.error(f"Action '{action_type}' denied: {msg}")
                return False

        # Inspect raw python payloads if present
        if "content" in payload and isinstance(payload["content"], str):
            valid, warnings = self.inspect_payload(payload["content"])
            if not valid:
                logger.error(f"Action '{action_type}' denied due to security policy.")
                return False

        return True