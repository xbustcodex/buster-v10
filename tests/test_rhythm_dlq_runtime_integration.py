from datetime import datetime
from pathlib import Path
import pytest

from buster.rhythm.dlq.models import DLQStatus, RecoveryStrategy
from buster.runtime.core import BusterRuntimeCore


def test_runtime_core_has_dlq_manager(tmp_path):
    core = BusterRuntimeCore(root=tmp_path)
    assert hasattr(core, "dlq_manager")
    assert core.dlq_manager is not None
    assert "dlq" in core.status()


def test_dlq_recovery_triggered_on_tick_during_work(tmp_path):
    core = BusterRuntimeCore(root=tmp_path)

    # Enqueue a work cycle task
    core.dlq_manager.enqueue(
        task_id="task_001",
        task_name="failed_index_job",
        payload={"execution_class": "background"},
        error="Connection Timeout",
        recovery_strategy=RecoveryStrategy.NEXT_WORK_CYCLE,
    )

    # Force rhythm to WORK state
    work_time = datetime(2026, 7, 22, 10, 0, 0)
    core.rhythm_service.tick_sync(now=work_time)

    # Query ready items directly
    ready = core.dlq_manager.get_ready_items(now=work_time)
    assert len(ready) == 1
    assert ready[0].task_id == "task_001"