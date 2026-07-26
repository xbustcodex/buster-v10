# tests/test_v24_social_and_strategy.py
import pytest
from buster.social.social_context import SocialContextEngine
from buster.cognitive.strategic_planner import StrategicPlanner


def test_social_context_engine(tmp_path):
    storage = tmp_path / "social_context.json"
    engine = SocialContextEngine(storage_path=storage)

    state = engine.update_context(
        user_mood="focused",
        noise_level="quiet",
        engagement_mode="development",
        note="User is writing test suites.",
    )

    assert state.user_mood == "focused"
    assert state.active_engagement_mode == "development"
    assert len(state.relational_notes) == 1
    assert "User is writing test suites." in state.relational_notes[0]


def test_strategic_planner_roadmap_generation(tmp_path):
    planner = StrategicPlanner(roadmap_dir=tmp_path)
    spec = planner.generate_spec(
        spec_id="phase_24_spec",
        title="Social Synthesis & Strategic Roadmap Engine",
        target_phase="Phase 24",
        objectives=["Establish social context modeling", "Enable autonomous spec generation"],
        hardware_deps=["processor", "memory"],
    )

    assert spec.spec_id == "phase_24_spec"
    assert spec.status == "drafted"
    assert len(spec.objectives) == 2

    files = list(tmp_path.glob("phase_24_spec.json"))
    assert len(files) == 1