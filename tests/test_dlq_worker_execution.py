from datetime import datetime
from pathlib import Path
import pytest

from buster.rhythm.dlq.models import DLQStatus, RecoveryStrategy
from buster.runtime.core import BusterRuntimeCore


def test_dlq_worker_processes_ready_items(tmp_path):
    core = BusterRuntimeCore(root=tmp_path)

    # Enqueue a task with NEXT_WORK_CYCLE strategy
    core.dlq_manager.enqueue(
        task_id="task_worker_01",
        task_name="background_sync",
        payload={"execution_class": "background"},
        error="Network Interrupted",
        recovery_strategy=RecoveryStrategy.NEXT_WORK_CYCLE,
    )

    # Target Monday morning 10:00 AM (WORK state)
    work_time = datetime(2026, 7, 20, 10, 0, 0)

    # Tick with explicit now timestamp
    core.tick(now=work_time)

    status = core.dlq_manager.status()
    assert status["resolved_items"] == 1
    assert status["pending_items"] == 0