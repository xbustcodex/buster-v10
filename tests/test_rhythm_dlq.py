from datetime import datetime
import pytest
from unittest.mock import MagicMock

from buster.rhythm.dlq.dlq_manager import RhythmDLQManager
from buster.rhythm.dlq.models import DLQStatus, RecoveryStrategy
from buster.rhythm.rhythm import BusterRhythm


@pytest.fixture
def dlq_manager(tmp_path):
    rhythm = BusterRhythm()
    storage = tmp_path / "dlq_state.json"
    event_bus = MagicMock()
    return RhythmDLQManager(rhythm=rhythm, storage_path=storage, event_bus=event_bus)


def test_enqueue_defaults_strategy_based_on_payload(dlq_manager):
    # Foreground task -> IMMEDIATE
    item1 = dlq_manager.enqueue(
        task_id="t1",
        task_name="user_request",
        payload={"execution_class": "foreground"},
        error="Runtime Error",
    )
    assert item1.recovery_strategy == RecoveryStrategy.IMMEDIATE

    # Experimental task -> DREAM_SANDBOX
    item2 = dlq_manager.enqueue(
        task_id="t2",
        task_name="self_heal",
        payload={"experimental": True},
        error="Code syntax issue",
    )
    assert item2.recovery_strategy == RecoveryStrategy.DREAM_SANDBOX


def test_get_ready_items_respects_rhythm_work_state(dlq_manager):
    # Enqueue a work cycle task
    dlq_manager.enqueue(
        task_id="t_work",
        task_name="background_index",
        payload={"execution_class": "background"},
        error="Timeout",
        recovery_strategy=RecoveryStrategy.NEXT_WORK_CYCLE,
    )

    # 1. Evaluate at SLEEP hours (03:00 AM)
    sleep_time = datetime(2026, 7, 22, 3, 0, 0)
    ready_night = dlq_manager.get_ready_items(now=sleep_time)
    assert len(ready_night) == 0

    # 2. Evaluate at WORK hours (Wednesday 10:00 AM)
    work_time = datetime(2026, 7, 22, 10, 0, 0)
    ready_day = dlq_manager.get_ready_items(now=work_time)
    assert len(ready_day) == 1
    assert ready_day[0].task_id == "t_work"


def test_dream_sandbox_items_ready_during_sleep(dlq_manager):
    dlq_manager.enqueue(
        task_id="t_dream",
        task_name="ai_self_improvement",
        payload={"experimental": True},
        error="Assertion failed",
        recovery_strategy=RecoveryStrategy.DREAM_SANDBOX,
    )

    sleep_time = datetime(2026, 7, 22, 3, 0, 0)
    ready = dlq_manager.get_ready_items(now=sleep_time)
    assert len(ready) == 1
    assert ready[0].task_id == "t_dream"