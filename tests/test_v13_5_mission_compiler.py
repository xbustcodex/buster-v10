"""
Test v13.4: Mission Compiler Layer
"""
import pytest
from buster.autonomy.goals.mission_compiler import MissionCompiler, MissionSpec
from buster.autonomy.goals.models import GoalProposal


def test_mission_compiler_translation():
    compiler = MissionCompiler()

    proposal = GoalProposal(
        title="Rebuild Project Index",
        request="Scan codebase and generate json index",
        target="/workspace/src",
        signal_id="sig_index_001",
    )

    mission = compiler.compile(proposal, evidence={"changed_files": 3})

    assert isinstance(mission, MissionSpec)
    assert mission.goal_id == proposal.id
    assert mission.mission_id == f"mission_{proposal.id}"
    assert len(mission.steps) == 3
    assert mission.steps[0]["action"] == "scan_directory"
    assert mission.context["evidence"]["changed_files"] == 3