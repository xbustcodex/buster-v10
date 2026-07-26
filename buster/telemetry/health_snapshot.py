from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from buster.telemetry.metrics_registry import MetricsRegistry


class HealthSnapshot:
    """Evaluates metrics and component states to produce system health summaries."""

    @staticmethod
    def generate(metrics: MetricsRegistry) -> Dict[str, Any]:
        """Calculates system status ('HEALTHY', 'DEGRADED', 'CRITICAL') based on metric ratios."""
        snap = metrics.snapshot()
        counters = snap.get("counters", {})

        total_execs = counters.get("execution.started", 0)
        total_fails = counters.get("execution.failed", 0)
        cb_trips = counters.get("circuit.opened", 0)

        failure_rate = (total_fails / total_execs) if total_execs > 0 else 0.0

        if cb_trips > 0 or failure_rate >= 0.5:
            status = "DEGRADED"
        elif failure_rate >= 0.8:
            status = "CRITICAL"
        else:
            status = "HEALTHY"

        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_executions": total_execs,
            "total_failures": total_fails,
            "failure_rate": round(failure_rate, 4),
            "circuit_breaker_trips": cb_trips,
            "metrics_summary": snap,
        }