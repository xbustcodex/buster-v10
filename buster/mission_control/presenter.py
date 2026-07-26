# buster/mission_control/presenter.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from buster.mission_control.snapshot import (
    MissionControlSnapshot,
    WorkerLeaseSnapshot,
    CircuitSnapshot,
)
from buster.mission_control.health_aggregator import HealthAggregator


class MissionControlPresenter:
    """Collects runtime state across backend subsystems and converts it to an immutable snapshot."""

    def __init__(
        self,
        telemetry: Any,
        worker_pool: Any,
        circuit_registry: Any,
        delegation_planner: Optional[Any] = None,
        learning_system: Optional[Any] = None,
        dlq_repository: Optional[Any] = None,
        health_aggregator: Optional[HealthAggregator] = None,
    ):
        self.telemetry = telemetry
        self.worker_pool = worker_pool
        self.circuit_registry = circuit_registry
        self.delegation_planner = delegation_planner
        self.learning_system = learning_system
        self.dlq_repository = dlq_repository
        self.health_aggregator = health_aggregator or HealthAggregator()

    def create_snapshot(self) -> MissionControlSnapshot:
        now = datetime.now(timezone.utc)

        # 1. Collect Worker Leases
        active_leases_list: List[WorkerLeaseSnapshot] = []
        expired_unreclaimed = False
        if hasattr(self.worker_pool, "active_leases"):
            for lease_id, lease in self.worker_pool.active_leases.items():
                rem = getattr(lease, "time_remaining", lambda: 0.0)()
                if rem <= 0:
                    expired_unreclaimed = True
                
                acq_at = getattr(lease, "acquired_at", now)
                exp_at = getattr(lease, "expires_at", now)

                active_leases_list.append(
                    WorkerLeaseSnapshot(
                        lease_id=str(lease_id),
                        worker_id=getattr(lease, "agent_id", "worker_unknown"),
                        role=getattr(lease, "role", "Worker"),
                        task_id=getattr(lease, "task_id", "task_unknown"),
                        acquired_at=acq_at if isinstance(acq_at, datetime) else now,
                        expires_at=exp_at if isinstance(exp_at, datetime) else now,
                        remaining_seconds=max(0.0, float(rem)),
                    )
                )

        # 2. Collect Circuit Breakers
        circuit_snapshots: List[CircuitSnapshot] = []
        open_critical = 0
        open_noncritical = 0

        circuits = getattr(self.circuit_registry, "circuits", {})
        if isinstance(circuits, dict):
            for cid, cb in circuits.items():
                state = getattr(cb, "state", "CLOSED")
                is_crit = getattr(cb, "is_critical", False)
                if state == "OPEN":
                    if is_crit:
                        open_critical += 1
                    else:
                        open_noncritical += 1

                circuit_snapshots.append(
                    CircuitSnapshot(
                        circuit_id=str(cid),
                        state=str(state),
                        failure_count=int(getattr(cb, "failure_count", 0)),
                        retry_after_seconds=getattr(cb, "retry_after_seconds", None),
                        is_critical=is_crit,
                    )
                )

        # 3. Collect Telemetry & DLQ Metrics
        tele_health = self.telemetry.get_health() if hasattr(self.telemetry, "get_health") else {}
        total_exec = tele_health.get("total_executions", 0)
        total_fail = tele_health.get("total_failures", 0)

        dlq_count = 0
        if self.dlq_repository and hasattr(self.dlq_repository, "count"):
            dlq_count = self.dlq_repository.count()

        # 4. Determine Health Status
        health_status = self.health_aggregator.calculate(
            open_critical_circuits=open_critical,
            open_noncritical_circuits=open_noncritical,
            dlq_count=dlq_count,
            telemetry_stale=False,
            worker_pool_available=True,
            has_expired_unreclaimed_leases=expired_unreclaimed,
        )

        # 5. Extract Insights
        insights: Tuple[Dict[str, Any], ...] = ()
        if self.learning_system and hasattr(self.learning_system, "get_insights"):
            insights = tuple(self.learning_system.get_insights())

        # 6. Extract Delegation Tree
        tree = {}
        if self.delegation_planner and hasattr(self.delegation_planner, "get_tree"):
            tree = self.delegation_planner.get_tree()

        return MissionControlSnapshot(
            generated_at=now,
            health=health_status,
            active_tasks=len(active_leases_list),
            queued_tasks=0,
            completed_tasks=max(0, total_exec - total_fail),
            failed_tasks=total_fail,
            dlq_count=dlq_count,
            active_leases=tuple(active_leases_list),
            circuits=tuple(circuit_snapshots),
            metrics={
                "failure_rate": float(tele_health.get("failure_rate", 0.0)),
                "circuit_trips": float(tele_health.get("circuit_breaker_trips", 0)),
            },
            insights=insights,
            delegation_tree=tree,
        )