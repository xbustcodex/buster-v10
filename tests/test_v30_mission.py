# tests/test_v30_mission.py
import pytest
from buster.autonomy.mission_state import Mission, AutonomyPolicy


def test_mission_created_with_trace_and_policy():
    policy = AutonomyPolicy(
        level=2,
        allow_file_writes=True,
        allow_shell_commands=True,
        allow_network_access=False,
        allow_process_control=False,
        allow_self_patch=False,
        require_approval_for_merge=True,
        maximum_runtime_minutes=30,
        maximum_child_tasks=10,
    )

    mission = Mission(
        mission_id="mission_test_01",
        objective="Add feature X and verify",
        status="CREATED",
        priority=1,
        created_at="2026-07-26T03:48:26Z",
        current_stage="INITIALIZATION",
        success_criteria=["Tests pass successfully"],
        trace_id="trace_abc123",
        autonomy_policy=policy,
    )

    assert mission.mission_id == "mission_test_01"
    assert mission.status == "CREATED"
    assert mission.trace_id == "trace_abc123"
    assert mission.autonomy_policy is not None
    assert mission.autonomy_policy.level == 2
    assert mission.autonomy_policy.allow_shell_commands is True