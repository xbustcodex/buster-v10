"""
Test v13.5: Goal Dashboard & Intent UI Summary
"""
import pytest
from buster.autonomy.goals.dashboard import GoalDashboard
from buster.autonomy.goals.models import GoalProposal
from buster.autonomy.goals.registry import GoalRegistry
from buster.autonomy.goals.storage import GoalStorage


def test_goal_dashboard_summary(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    dashboard = GoalDashboard(registry=registry)

    # 1. Register test proposals
    prop1 = GoalProposal(title="Index Repository", request="Update index", target="/src", signal_id="sig_1")
    prop2 = GoalProposal(title="Fix Duplicate Import", request="Refactor", target="/src/main.py", signal_id="sig_2")

    registry.register_proposal(prop1, evidence={"size_mb": 12})
    goal2 = registry.register_proposal(prop2, evidence={"line": 42})

    # Update goal states
    registry.update_status(goal2["id"], "EXECUTING")

    # 2. Get dashboard state
    summary = dashboard.get_dashboard_summary()

    assert summary["counts"]["total"] == 2
    assert summary["counts"]["active"] == 1
    assert summary["counts"]["waiting_approval"] == 1
    assert summary["active_goals"][0]["title"] == "Fix Duplicate Import"
    assert summary["waiting_approval"][0]["evidence"]["size_mb"] == 12