# tests/test_v30_next_action.py
import pytest
from buster.autonomy.mission_state import Mission, AutonomyPolicy
from buster.autonomy.observation_engine import Observation
from buster.autonomy.next_action_selector import NextActionSelector


def test_next_action_delegates_fixer():
    selector = NextActionSelector()
    mission = Mission(
        mission_id="m_01",
        objective="Fix test bug",
        status="EXECUTING",
        priority=1,
        created_at="2026-07-26T03:55:17Z",
        current_stage="EXECUTING",
    )
    obs = Observation(
        observation_id="obs_1",
        mission_id="m_01",
        source="tester",
        type="test.failed",
        importance=0.9,
        requires_replan=True,
    )

    decision = selector.select_next_action(mission, obs)

    assert decision.action_type == "delegate_fixer"
    assert decision.target_agent == "FixerAgent"


def test_permission_failure_requests_intervention():
    selector = NextActionSelector()
    mission = Mission(
        mission_id="m_02",
        objective="Execute restricted cmd",
        status="EXECUTING",
        priority=1,
        created_at="2026-07-26T03:55:17Z",
        current_stage="EXECUTING",
    )
    obs = Observation(
        observation_id="obs_2",
        mission_id="m_02",
        source="shell",
        type="permission.denied",
        importance=1.0,
        requires_replan=True,
    )

    decision = selector.select_next_action(mission, obs)

    assert decision.action_type == "request_approval"
    assert decision.requires_intervention is True