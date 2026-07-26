import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from buster.rhythm.rhythm import BusterRhythm, LifeState
from buster.rhythm.rhythm_service import RhythmService
from buster.rhythm.task_gate import TaskGate


@pytest.fixture
def mock_blackboard():
    class MockBlackboard:
        def __init__(self):
            self.data = {}
        def update(self, key, value):
            self.data[key] = value
    return MockBlackboard()


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = AsyncMock()
    return bus


@pytest.mark.asyncio
async def test_runtime_registers_rhythm_service(mock_blackboard, mock_event_bus):
    rhythm = BusterRhythm()
    service = RhythmService(rhythm, mock_blackboard, mock_event_bus)
    
    # Simulate a Wednesday 10:00 AM (WORK mode)
    work_time = datetime(2026, 7, 22, 10, 0, 0)
    status = await service.tick(now=work_time)

    assert mock_blackboard.data["rhythm"]["life_state"] == "WORK"
    assert mock_blackboard.data["rhythm"]["goal_inhibitor_active"] is False
    mock_event_bus.publish.assert_any_call("rhythm.work_started", status)


@pytest.mark.asyncio
async def test_dream_cycle_starts_on_sleep_transition(mock_blackboard, mock_event_bus):
    rhythm = BusterRhythm()
    service = RhythmService(rhythm, mock_blackboard, mock_event_bus)

    # Simulate 03:00 AM (SLEEP mode)
    sleep_time = datetime(2026, 7, 22, 3, 0, 0)
    status = await service.tick(now=sleep_time)

    assert mock_blackboard.data["rhythm"]["life_state"] == "SLEEP"
    assert mock_blackboard.data["rhythm"]["dream_sandbox_active"] is True
    mock_event_bus.publish.assert_any_call("dream_cycle.requested", status)


def test_goal_inhibitor_blocks_background_goal():
    rhythm_status = {"life_state": "LEISURE"}
    task_meta = {
        "priority": "high",
        "execution_class": "background",
        "allowed_states": ["WORK", "LEISURE"],
    }
    
    allowed, reason = TaskGate.evaluate(task_meta, rhythm_status)
    assert allowed is False
    assert "inhibited" in reason


def test_user_command_can_override_sleep_inhibitor():
    rhythm_status = {"life_state": "SLEEP"}
    task_meta = {
        "execution_class": "foreground",
        "can_override_inhibitor": True,
        "allowed_states": ["WORK", "LEISURE", "SLEEP"],
    }

    allowed, reason = TaskGate.evaluate(task_meta, rhythm_status)
    assert allowed is True
    assert "User override" in reason


def test_maintenance_task_allowed_during_sleep():
    rhythm_status = {"life_state": "SLEEP"}
    task_meta = {
        "execution_class": "background",
        "maintenance_safe": True,
        "allowed_states": ["WORK", "LEISURE", "SLEEP"],
    }

    allowed, reason = TaskGate.evaluate(task_meta, rhythm_status)
    assert allowed is True
    assert "Maintenance safe" in reason