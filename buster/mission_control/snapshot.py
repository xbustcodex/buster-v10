# buster/mission_control/snapshot.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Tuple, Optional


@dataclass(frozen=True, slots=True)
class WorkerLeaseSnapshot:
    lease_id: str
    worker_id: str
    role: str
    task_id: str
    acquired_at: datetime
    expires_at: datetime
    remaining_seconds: float


@dataclass(frozen=True, slots=True)
class CircuitSnapshot:
    circuit_id: str
    state: str  # "CLOSED", "HALF_OPEN", "OPEN"
    failure_count: int
    retry_after_seconds: Optional[float] = None
    is_critical: bool = False


@dataclass(frozen=True, slots=True)
class MissionControlSnapshot:
    generated_at: datetime
    health: str  # "HEALTHY", "DEGRADED", "CRITICAL"
    active_tasks: int
    queued_tasks: int
    completed_tasks: int
    failed_tasks: int
    dlq_count: int
    active_leases: Tuple[WorkerLeaseSnapshot, ...] = ()
    circuits: Tuple[CircuitSnapshot, ...] = ()
    metrics: Dict[str, float] = field(default_factory=dict)
    insights: Tuple[Dict[str, Any], ...] = ()
    delegation_tree: Dict[str, Any] = field(default_factory=dict)