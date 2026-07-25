"""
Test v13.2: Curiosity Loop Integration & Tick Heartbeat
"""
import pytest
from buster.autonomy.goals.curiosity_bridge import CuriosityBridge
from buster.autonomy.goals.goal_service import GoalService
from buster.autonomy.goals.registry import GoalRegistry
from buster.autonomy.goals.storage import GoalStorage


def test_curiosity_loop_bridge(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    goal_service = GoalService()
    bridge = CuriosityBridge(goal_service=goal_service, registry=registry)

    target_file = "/workspace/project/index.json"

    # 1. First observation triggers signal and creates persistent proposal
    goal = bridge.process_observation(
        signal_type="stale_index",
        target=target_file,
        metadata={"age_hours": 48},
        cooldown_seconds=60.0,
    )

    assert goal is not None
    assert goal["target"] == target_file
    assert goal["status"] == "PROPOSED"

    # Simulate evaluating and executing the goal to put it on active cooldown
    goal_service.statuses[goal["id"]] = "APPROVED"
    registry.update_status(goal["id"], "COMPLETED")

    # 2. Second tick observation for same target within cooldown should be ignored
    duplicate_goal = bridge.process_observation(
        signal_type="stale_index",
        target=target_file,
        metadata={"age_hours": 48},
        cooldown_seconds=60.0,
    )

    assert duplicate_goal is None