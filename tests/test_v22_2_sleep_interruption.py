import pytest
from buster.rhythm.rhythm import LifeState
from buster.rhythm.sleep_handler import SleepInterruptionHandler


def test_sleep_handler_awake_state():
    handler = SleepInterruptionHandler(dnd_enabled=False)
    resp = handler.process_prompt_during_sleep("Run task", current_state=LifeState.WORK)

    assert resp.interrupted is False
    assert resp.mode == "AWAKE"
    assert resp.allow_execution is True


def test_sleep_handler_groggy_mode():
    handler = SleepInterruptionHandler(dnd_enabled=False)
    resp = handler.process_prompt_during_sleep("What time is it?", current_state=LifeState.SLEEP)

    assert resp.interrupted is True
    assert resp.mode == "GROGGY"
    assert resp.allow_execution is True
    assert "yawn" in resp.message.lower()


def test_sleep_handler_dnd_mode_blocked():
    handler = SleepInterruptionHandler(dnd_enabled=True)
    resp = handler.process_prompt_during_sleep("What time is it?", current_state=LifeState.SLEEP)

    assert resp.interrupted is False
    assert resp.mode == "DND"
    assert resp.allow_execution is False


def test_sleep_handler_dnd_override_urgent():
    handler = SleepInterruptionHandler(dnd_enabled=True)
    resp = handler.process_prompt_during_sleep("Emergency! Wake up now!", current_state=LifeState.SLEEP)

    assert resp.interrupted is True
    assert resp.mode == "AWAKE"
    assert resp.allow_execution is True