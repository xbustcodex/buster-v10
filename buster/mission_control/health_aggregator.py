# buster/mission_control/health_aggregator.py
from __future__ import annotations


class HealthAggregator:
    """Calculates deterministic system health status based on control plane metrics."""

    def calculate(
        self,
        *,
        open_critical_circuits: int,
        open_noncritical_circuits: int,
        dlq_count: int,
        telemetry_stale: bool,
        worker_pool_available: bool,
        has_expired_unreclaimed_leases: bool = False,
    ) -> str:
        # Rule 1: CRITICAL condition overrides all
        if (
            open_critical_circuits > 0
            or not worker_pool_available
            or telemetry_stale
        ):
            return "CRITICAL"

        # Rule 2: DEGRADED condition
        if (
            open_noncritical_circuits > 0
            or dlq_count > 0
            or has_expired_unreclaimed_leases
        ):
            return "DEGRADED"

        # Rule 3: All checks green
        return "HEALTHY"