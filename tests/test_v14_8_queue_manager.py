"""
Test v14.8: Goal Queue Prioritization & Garbage Collection
"""
import time
import pytest
from buster.autonomy.goals.models import GoalProposal
from buster.autonomy.goals.queue_manager import GoalQueueManager
from buster.autonomy.goals.registry import GoalRegistry
from buster.autonomy.goals.storage import GoalStorage


def test_queue_prioritization(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    queue_mgr = GoalQueueManager(registry=registry)

    # Register goals with different priorities
    prop_normal = GoalProposal(title="Normal Task", request="R1", target="/t1", signal_id="sig_1")
    prop_critical = GoalProposal(title="Critical Task", request="R2", target="/t2", signal_id="sig_2")

    g_normal = registry.register_proposal(prop_normal, evidence={})
    g_critical = registry.register_proposal(prop_critical, evidence={})

    # Elevate critical priority
    g_critical["priority"] = "CRITICAL"
    registry.storage.save_goal(g_critical)

    prioritized = queue_mgr.get_prioritized_queue()
    assert len(prioritized) == 2
    assert prioritized[0]["title"] == "Critical Task"
    assert prioritized[1]["title"] == "Normal Task"


def test_garbage_collection(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    queue_mgr = GoalQueueManager(registry=registry)

    prop = GoalProposal(title="Old Task", request="R1", target="/t1", signal_id="sig_1")
    goal = registry.register_proposal(prop, evidence={})

    # Mark completed with an old timestamp
    registry.update_status(goal["id"], "COMPLETED")
    stale_goal = registry.get(goal["id"])
    stale_goal["last_execution_ts"] = time.time() - 100000.0  # > 1 day ago
    registry.storage.save_goal(stale_goal)

    gc_res = queue_mgr.garbage_collect_stale_goals(max_age_seconds=86400.0)
    assert gc_res["status"] == "success"
    assert gc_res["purged_count"] == 1
    assert len(registry.all_goals()) == 0