from __future__ import annotations

import enum
from typing import Any, Dict, Optional


class ErrorCategory(str, enum.Enum):
    TRANSIENT = "TRANSIENT"  # Temporary network/timeout, retryable immediately
    PERMISSION = "PERMISSION"  # Access denied / missing permissions
    MISSING_RESOURCE = "MISSING_RESOURCE"  # File or dependency not found
    SYNTAX_OR_CODE = "SYNTAX_OR_CODE"  # Code/script bug, needs fix before retrying
    CRITICAL = "CRITICAL"  # System failure, abort task


class ErrorDiagnostic:
    """Diagnoses execution errors and recommends recovery actions."""

    @staticmethod
    def classify_exception(exc: Exception) -> Dict[str, Any]:
        """Classifies a Python Exception into an ErrorCategory with retry recommendation."""
        exc_type = type(exc).__name__
        exc_msg = str(exc)

        if isinstance(exc, (FileNotFoundError, KeyError)):
            category = ErrorCategory.MISSING_RESOURCE
            retryable = False
        elif isinstance(exc, (PermissionError, OSError)) and "permission" in exc_msg.lower():
            category = ErrorCategory.PERMISSION
            retryable = False
        elif isinstance(exc, (TimeoutError, ConnectionError)):
            category = ErrorCategory.TRANSIENT
            retryable = True
        elif isinstance(exc, (SyntaxError, TypeError, ValueError)):
            category = ErrorCategory.SYNTAX_OR_CODE
            retryable = False
        else:
            category = ErrorCategory.CRITICAL
            retryable = False

        return {
            "error_type": exc_type,
            "message": exc_msg,
            "category": category.value,
            "retryable": retryable,
        }