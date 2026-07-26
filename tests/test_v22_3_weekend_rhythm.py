from datetime import datetime
import pytest
from buster.rhythm.rhythm import LifeState
from buster.rhythm.weekend_manager import WeekendRhythmManager


def test_weekday_evaluation():
    manager = WeekendRhythmManager()
    # Wednesday, July 22, 2026 at 10:00 AM
    wednesday = datetime(2026, 7, 22, 10, 0, 0)
    res = manager.evaluate_weekend_state(dt=wednesday)

    assert res["is_weekend"] is False
    assert res["override_state"] is None
    assert res["work_inhibited"] is False


def test_weekend_leisure_window():
    manager = WeekendRhythmManager(start_hour=8, leisure_hours=16)
    # Saturday, July 25, 2026 at 2:00 PM
    saturday_afternoon = datetime(2026, 7, 25, 14, 0, 0)
    res = manager.evaluate_weekend_state(dt=saturday_afternoon)

    assert res["is_weekend"] is True
    assert res["override_state"] == LifeState.LEISURE
    assert res["work_inhibited"] is True
    assert res["deep_dream_eligible"] is False


def test_weekend_deep_dream_window():
    manager = WeekendRhythmManager(start_hour=8, leisure_hours=16)
    # Sunday, July 26, 2026 at 3:00 AM
    sunday_night = datetime(2026, 7, 26, 3, 0, 0)
    res = manager.evaluate_weekend_state(dt=sunday_night)

    assert res["is_weekend"] is True
    assert res["override_state"] == LifeState.SLEEP
    assert res["work_inhibited"] is True
    assert res["deep_dream_eligible"] is True