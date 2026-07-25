from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional, Tuple
from buster.autonomy.recovery.diagnostics import ErrorDiagnostic


class ResilientExecutionRunner:
    """Executes callables with automatic retry policies and fallback mechanisms based on error diagnostics."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 0.1):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def execute_with_retry(
        self,
        fn: Callable[..., Any],
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        fallback_fn: Optional[Callable[..., Any]] = None,
    ) -> Dict[str, Any]:
        """Runs a function with retry on transient errors and optional fallback on persistent errors."""
        kwargs = kwargs or {}
        attempts = 0
        last_diagnostic = None

        while attempts <= self.max_retries:
            attempts += 1
            try:
                result = fn(*args, **kwargs)
                return {
                    "status": "success",
                    "attempts": attempts,
                    "result": result,
                    "fallback_used": False,
                }
            except Exception as exc:
                last_diagnostic = ErrorDiagnostic.classify_exception(exc)

                # Only retry if the error is retryable and attempts remain
                if last_diagnostic["retryable"] and attempts <= self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** (attempts - 1))
                    time.sleep(sleep_time)
                    continue
                else:
                    break

        # Attempt fallback if available
        if fallback_fn is not None:
            try:
                fallback_result = fallback_fn(*args, **kwargs)
                return {
                    "status": "success",
                    "attempts": attempts,
                    "result": fallback_result,
                    "fallback_used": True,
                    "diagnostic": last_diagnostic,
                }
            except Exception as fallback_exc:
                fallback_diag = ErrorDiagnostic.classify_exception(fallback_exc)
                return {
                    "status": "failed",
                    "attempts": attempts,
                    "error": str(fallback_exc),
                    "diagnostic": fallback_diag,
                    "fallback_used": True,
                }

        return {
            "status": "failed",
            "attempts": attempts,
            "error": last_diagnostic["message"] if last_diagnostic else "Execution failed",
            "diagnostic": last_diagnostic,
            "fallback_used": False,
        }