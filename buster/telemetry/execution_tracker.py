from __future__ import annotations

import time
from typing import Any, Dict, Optional
from buster.telemetry.event_logger import EventLogger
from buster.telemetry.metrics_registry import MetricsRegistry
from buster.autonomy.recovery.diagnostics import ErrorDiagnostic


class ExecutionTracker:
    """Context manager for tracing callable execution, logging start/completion/failures, and timing performance."""

    def __init__(
        self,
        component: str,
        logger: EventLogger,
        metrics: MetricsRegistry,
        event_prefix: str = "execution",
        attempt: int = 1,
    ):
        self.component = component
        self.logger = logger
        self.metrics = metrics
        self.event_prefix = event_prefix
        self.attempt = attempt
        self.start_time = 0.0

    def __enter__(self) -> ExecutionTracker:
        self.start_time = time.time()
        self.metrics.increment(f"{self.event_prefix}.started")
        self.logger.log_event(
            event_type=f"{self.event_prefix}.started",
            component=self.component,
            status="running",
            attempt=self.attempt,
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        duration_ms = (time.time() - self.start_time) * 1000.0
        self.metrics.observe_duration(self.component, duration_ms)

        if exc_type is not None:
            self.metrics.increment(f"{self.event_prefix}.failed")
            diag = ErrorDiagnostic.classify_exception(exc_val)
            self.logger.log_event(
                event_type=f"{self.event_prefix}.failed",
                component=self.component,
                status="failed",
                duration_ms=duration_ms,
                attempt=self.attempt,
                failure_category=diag["category"],
                retryable=diag["retryable"],
                extra={"error": str(exc_val)},
            )
            return False  # Propagate exception

        self.metrics.increment(f"{self.event_prefix}.completed")
        self.logger.log_event(
            event_type=f"{self.event_prefix}.completed",
            component=self.component,
            status="success",
            duration_ms=duration_ms,
            attempt=self.attempt,
        )
        return True