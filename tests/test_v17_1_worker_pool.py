"""
Test v17.1: Worker Pool Manager & Task Leases
"""
import time
import pytest
from buster.autonomy.delegation.worker_pool import WorkerPoolManager, TaskLeaseExpiredException


def test_acquire_and_release_lease():
    pool = WorkerPoolManager(max_concurrency=2, default_lease_timeout=10.0)

    lease = pool.acquire_lease(task_id="task_builder_1", agent_id="worker_builder")
    assert pool.active_count() == 1
    assert pool.validate_lease(lease.lease_id) is True

    released = pool.release_lease(lease.lease_id)
    assert released is True
    assert pool.active_count() == 0


def test_concurrency_limit_enforced():
    pool = WorkerPoolManager(max_concurrency=1, default_lease_timeout=10.0)

    pool.acquire_lease(task_id="task_1", agent_id="agent_alpha")
    assert pool.active_count() == 1

    with pytest.raises(RuntimeError, match="concurrency limit reached"):
        pool.acquire_lease(task_id="task_2", agent_id="agent_beta")


def test_lease_expiration_and_reclamation():
    pool = WorkerPoolManager(max_concurrency=2, default_lease_timeout=0.1)

    lease = pool.acquire_lease(task_id="short_task", agent_id="worker_fast")
    assert pool.active_count() == 1

    time.sleep(0.15)

    # Validate should mark it expired and release it automatically
    assert pool.validate_lease(lease.lease_id) is False
    assert pool.active_count() == 0