# tests/test_v24_3_spec_evaluator.py
import json
import pytest
from buster.hurdle.spec_evaluator import AutonomousSpecEvaluator
from buster.cognitive.strategic_planner import StrategicPlanner


def test_autonomous_spec_evaluator(tmp_path):
    ledger_file = tmp_path / "growth_ledger.json"
    roadmap_dir = tmp_path / "roadmaps"

    # Seed growth ledger with test hurdles
    ledger_data = {
        "hurdles": [
            {"error_message": "ConnectionTimeout in background sync worker", "timestamp": "2026-07-26T12:00:00Z"},
            {"error_message": "ConnectionTimeout in background sync worker", "timestamp": "2026-07-26T12:05:00Z"},
            {"error_message": "AssertionError in perception loop", "timestamp": "2026-07-26T12:10:00Z"},
        ]
    }
    ledger_file.write_text(json.dumps(ledger_data), encoding="utf-8")

    planner = StrategicPlanner(roadmap_dir=roadmap_dir)
    evaluator = AutonomousSpecEvaluator(growth_ledger_path=ledger_file, strategic_planner=planner)

    spec = evaluator.evaluate_and_propose_spec(target_phase="Phase 25")

    assert spec is not None
    assert "ConnectionTimeout" in spec.title
    assert spec.target_phase == "Phase 25"
    assert len(spec.objectives) == 3

    # Verify spec file exists on disk
    spec_files = list(roadmap_dir.glob("*.json"))
    assert len(spec_files) == 1