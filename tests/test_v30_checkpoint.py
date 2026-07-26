# tests/test_v30_checkpoint.py
import pytest
from buster.autonomy.mission_state import Mission, AutonomyPolicy
from buster.autonomy.loop_checkpoint import MissionCheckpointManager


def test_mission_checkpoint_written_on_transition(tmp_path):
    manager = MissionCheckpointManager(storage_dir=tmp_path)
    policy = AutonomyPolicy(
        level=2,
        allow_file_writes=True,
        allow_shell_commands=True,
        allow_network_access=False,
        allow_process_control=False,
        allow_self_patch=False,
        require_approval_for_merge=True,
        maximum_runtime_minutes=30,
        maximum_child_tasks=5,
    )
    mission = Mission(
        mission_id="m_chk_1",
        objective="Test persistence",
        status="EXECUTING",
        priority=1,
        created_at="2026-07-26T04:00:00Z",
        current_stage="EXECUTING",
        autonomy_policy=policy,
    )

    checkpoint = manager.save_checkpoint(mission, active_leases=["worker_1"], circuit_states={"api": "CLOSED"})
    assert checkpoint.checkpoint_id is not None
    assert mission.checkpoint_id == checkpoint.checkpoint_id

    # Simulate runtime restart by loading from manager
    recovered_mission = manager.recover_mission("m_chk_1")
    assert recovered_mission is not None
    assert recovered_mission.mission_id == "m_chk_1"
    assert recovered_mission.status == "EXECUTING"
    assert recovered_mission.autonomy_policy.level == 2