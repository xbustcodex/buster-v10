import json
import pytest
from buster.cognitive.milestone_reporter import MilestoneReporter
from buster.learning.preference_memory import PersonalPreferenceMemory


def test_preference_memory_save_and_load(tmp_path):
    json_path = tmp_path / "interests.json"
    memory = PersonalPreferenceMemory(storage_path=json_path)

    memory.record_exploration(
        topic="asyncio_event_loop",
        category="code_pattern",
        affinity_score=0.85,
        note="Explored task cancellation handlers.",
    )

    assert json_path.exists()

    # Re-instantiate to test persistence
    memory_reloaded = PersonalPreferenceMemory(storage_path=json_path)
    top = memory_reloaded.get_top_interests(limit=1)

    assert len(top) == 1
    assert top[0].topic == "asyncio_event_loop"
    assert top[0].affinity_score == 0.85
    assert "Explored task cancellation handlers." in top[0].notes


def test_milestone_reporter_generation(tmp_path):
    reporter = MilestoneReporter(log_dir=tmp_path)

    patches = [{"hurdle_id": "h_001", "target_file": "brain/core.py", "summary": "Fixed Null Pointer handling"}]
    explorations = [{"target_path": "learning/curiosity_evaluator.py", "curiosity_score": 12.5}]

    summary = reporter.generate_report(
        patches=patches,
        explorations=explorations,
        dreams_count=3,
        failures_count=0,
    )

    assert summary.dreams_executed == 3
    assert len(summary.patches_applied) == 1
    assert len(summary.curiosity_tasks_completed) == 1

    # Check generated report file
    files = list(tmp_path.glob("milestone_*.json"))
    assert len(files) == 1

    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["dreams_executed"] == 3
    assert data["patches_applied"][0]["hurdle_id"] == "h_001"