"""
Test v13.6: Memory Synthesis for Completed Goals
"""
import pytest
from buster.autonomy.goals.memory_synthesizer import MemorySynthesizer
from buster.autonomy.goals.models import GoalProposal
from buster.autonomy.goals.registry import GoalRegistry
from buster.autonomy.goals.storage import GoalStorage


def test_memory_synthesis_on_completion(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    synthesizer = MemorySynthesizer(registry=registry)

    # 1. Register and complete a goal
    proposal = GoalProposal(
        title="Repair Duplicate Providers",
        request="Refactor redundant provider definitions",
        target="/src/providers",
        signal_id="sig_dup_001",
    )
    goal_data = registry.register_proposal(proposal, evidence={"duplicates": 2})
    registry.update_status(goal_data["id"], "COMPLETED", result={"fixed": 2})

    # 2. Synthesize long-term memory pattern
    memory = synthesizer.synthesize_completed_goal(goal_data["id"])

    assert memory is not None
    assert memory["goal_id"] == goal_data["id"]
    assert memory["success"] is True
    assert memory["confidence_boost"] == 0.05

    # 3. Verify pattern can be recalled for future decisions
    recalled = synthesizer.get_pattern_experience("/src/providers")
    assert recalled is not None
    assert recalled["title"] == "Repair Duplicate Providers"