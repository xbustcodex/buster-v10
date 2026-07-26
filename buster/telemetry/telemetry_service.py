from __future__ import annotations

from typing import Any, Dict, Optional
from buster.telemetry.event_logger import EventLogger
from buster.telemetry.metrics_registry import MetricsRegistry
from buster.telemetry.health_snapshot import HealthSnapshot
from buster.telemetry.execution_tracker import ExecutionTracker


class TelemetryService:
    """Unified orchestration service for logging, metrics aggregation, and health reporting."""

    def __init__(self, log_dir: str = "data"):
        self.logger = EventLogger(log_dir=log_dir)
        self.metrics = MetricsRegistry(metrics_file=f"{log_dir}/runtime_metrics.json")

    def track_execution(
        self,
        component: str,
        attempt: int = 1,
        event_prefix: str = "execution",
    ) -> ExecutionTracker:
        """Returns an ExecutionTracker context manager for tracing a block or callable."""
        return ExecutionTracker(
            component=component,
            logger=self.logger,
            metrics=self.metrics,
            event_prefix=event_prefix,
            attempt=attempt,
        )

    def record_retry(
        self,
        component: str,
        attempt: int,
        failure_category: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Logs a scheduled retry event."""
        self.metrics.increment("execution.retry_scheduled")
        self.logger.log_event(
            event_type="execution.retry_scheduled",
            component=component,
            status="warning",
            attempt=attempt,
            failure_category=failure_category,
            retryable=True,
            extra=extra,
        )

    def record_circuit_event(self, event_type: str, target_id: str) -> None:
        """Logs circuit breaker status transitions ('circuit.opened', 'circuit.closed', etc.)."""
        self.metrics.increment(event_type)
        self.logger.log_event(
            event_type=event_type,
            component="circuit_breaker",
            status="warning" if "opened" in event_type else "info",
            extra={"target_id": target_id},
        )

    def get_health(self) -> Dict[str, Any]:
        """Returns a real-time system health evaluation snapshot."""
        return HealthSnapshot.generate(self.metrics)

    def flush(self) -> None:
        """Persists metrics to disk."""
        self.metrics.save()