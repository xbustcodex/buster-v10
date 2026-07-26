from datetime import datetime
from unittest.mock import MagicMock
import pytest

from buster.learning.curiosity_evaluator import CuriosityEvaluator
from buster.learning.curiosity_scheduler import CuriosityScheduler
from buster.rhythm.rhythm import LifeState


def test_curiosity_scheduler_blocks_during_sleep(tmp_path):
    f = tmp_path / "complex.py"
    f.write_text("\n".join([f"x = {i}" for i in range(250)]), encoding="utf-8")

    evaluator = CuriosityEvaluator(project_root=tmp_path)
    mock_rhythm = MagicMock()
    mock_rhythm.get_blackboard_status.return_value = {"life_state": LifeState.SLEEP}

    scheduler = CuriosityScheduler(evaluator=evaluator, rhythm_service=mock_rhythm, min_score_threshold=0.0)
    tasks = scheduler.schedule_exploration()

    assert len(tasks) == 0


def test_curiosity_scheduler_schedules_during_work_or_leisure(tmp_path):
    f = tmp_path / "complex.py"
    f.write_text("\n".join([f"x = {i}" for i in range(250)]), encoding="utf-8")

    evaluator = CuriosityEvaluator(project_root=tmp_path)
    mock_rhythm = MagicMock()
    mock_rhythm.get_blackboard_status.return_value = {"life_state": LifeState.WORK}

    scheduler = CuriosityScheduler(evaluator=evaluator, rhythm_service=mock_rhythm, min_score_threshold=0.0)
    
    # Verify rhythm state check directly
    assert scheduler.is_exploration_allowed() is True

    tasks = scheduler.schedule_exploration(
        limit=1,
        context={"failure_counts": {str((tmp_path / "complex.py").resolve()): 1}}
    )

    assert len(tasks) == 1
    assert tasks[0].target_path.endswith("complex.py")
    assert tasks[0].execution_class == "background"