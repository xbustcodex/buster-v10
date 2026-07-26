from __future__ import annotations

import time
import uuid
import threading
from typing import Dict, Any, Optional, List


class TaskLeaseExpiredException(Exception):
    """Raised when an operation is attempted on an expired task lease."""
    pass


class TaskLease:
    """Represents an active task reservation held by a worker agent."""

    def __init__(self, lease_id: str, task_id: str, agent_id: str, timeout_sec: float):
        self.lease_id = lease_id
        self.task_id = task_id
        self.agent_id = agent_id
        self.timeout_sec = timeout_sec
        self.acquired_at = time.time()

    def is_expired(self) -> bool:
        """Checks if the lease has exceeded its allocated timeout."""
        return (time.time() - self.acquired_at) >= self.timeout_sec

    def time_remaining(self) -> float:
        """Returns remaining seconds before expiration."""
        rem = self.timeout_sec - (time.time() - self.acquired_at)
        return max(0.0, rem)


class WorkerPoolManager:
    """Manages worker agents, concurrency limits, and active task leases."""

    def __init__(self, max_concurrency: int = 4, default_lease_timeout: float = 30.0):
        self._lock = threading.RLock()
        self.max_concurrency = max_concurrency
        self.default_lease_timeout = default_lease_timeout
        self.active_leases: Dict[str, TaskLease] = {}  # lease_id -> TaskLease
        self.worker_assignments: Dict[str, str] = {}  # agent_id -> lease_id

    def acquire_lease(
        self,
        task_id: str,
        agent_id: str,
        timeout_sec: Optional[float] = None,
    ) -> TaskLease:
        """Attempts to acquire a task lease for a worker agent if concurrency allows."""
        with self._lock:
            # Clean up expired leases first
            self._reclaim_expired_leases()

            if len(self.active_leases) >= self.max_concurrency:
                raise RuntimeError(
                    f"Worker pool concurrency limit reached ({self.max_concurrency}). Cannot lease task '{task_id}'."
                )

            if agent_id in self.worker_assignments:
                raise RuntimeError(f"Agent '{agent_id}' already holds an active task lease.")

            lease_id = f"lse_{uuid.uuid4().hex[:8]}"
            timeout = timeout_sec if timeout_sec is not None else self.default_lease_timeout
            lease = TaskLease(
                lease_id=lease_id,
                task_id=task_id,
                agent_id=agent_id,
                timeout_sec=timeout,
            )

            self.active_leases[lease_id] = lease
            self.worker_assignments[agent_id] = lease_id
            return lease

    def release_lease(self, lease_id: str) -> bool:
        """Releases an active lease held by a worker."""
        with self._lock:
            if lease_id in self.active_leases:
                lease = self.active_leases.pop(lease_id)
                self.worker_assignments.pop(lease.agent_id, None)
                return True
            return False

    def validate_lease(self, lease_id: str) -> bool:
        """Verifies that a lease exists and has not expired."""
        with self._lock:
            lease = self.active_leases.get(lease_id)
            if not lease:
                return False
            if lease.is_expired():
                self.release_lease(lease_id)
                return False
            return True

    def _reclaim_expired_leases(self) -> List[str]:
        """Internal helper to drop expired leases."""
        expired = [lid for lid, lse in self.active_leases.items() if lse.is_expired()]
        for lid in expired:
            self.release_lease(lid)
        return expired

    def active_count(self) -> int:
        """Returns active lease count."""
        with self._lock:
            self._reclaim_expired_leases()
            return len(self.active_leases)