"""
Test v14.1: Goals REST API & Dashboard Controller
"""
import pytest
from buster.api.routes.goals import GoalsAPIController
from buster.autonomy.goals.models import GoalProposal
from buster.autonomy.goals.registry import GoalRegistry
from buster.autonomy.goals.storage import GoalStorage


def test_get_dashboard_and_goals(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    controller = GoalsAPIController(registry=registry)

    # 1. Register test proposal with required evidence dict
    prop = GoalProposal(
        title="Index Test Project",
        request="Scan codebase",
        target="/tmp/test",
        signal_id="sig_api_01",
    )
    registry.register_proposal(prop, evidence={"source": "api_test"})

    # 2. List goals
    res_goals = controller.list_goals()
    assert "goals" in res_goals
    assert len(res_goals["goals"]) == 1

    # 3. Get dashboard
    res_dash = controller.get_dashboard()
    assert "counts" in res_dash
    assert res_dash["counts"]["total"] == 1


def test_capabilities_management():
    controller = GoalsAPIController()

    # Get capabilities
    caps = controller.get_capabilities()
    assert "WRITE_FILES" in caps

    # Update permission
    update_res = controller.update_capability_policy("WRITE_FILES", "AUTO_APPROVE")
    assert update_res["status"] == "success"
    assert update_res["new_permission"] == "AUTO_APPROVE"


def test_manual_goal_decision(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    controller = GoalsAPIController(registry=registry)

    prop = GoalProposal(
        title="Index Test Project",
        request="Scan codebase",
        target="/tmp/test",
        signal_id="sig_api_01",
    )
    registered = registry.register_proposal(prop, evidence={"source": "api_test"})

    # Manually approve
    res = controller.decide_goal(registered["id"], action="APPROVE", reason="Verified by operator")
    assert res["status"] == "success"
    assert res["goal"]["status"] == "APPROVED"