"""
Test v14.3: Human-in-the-Loop Interventions & Emergency Lockdown
"""
import pytest
from buster.autonomy.goals.capabilities import Capability, CapabilityPolicy, ExecutionPermission
from buster.autonomy.goals.interventions import HumanInterventionManager
from buster.autonomy.goals.registry import GoalRegistry
from buster.autonomy.goals.storage import GoalStorage


def test_emergency_pause_toggle():
    manager = HumanInterventionManager()
    assert manager.is_system_paused is False

    # Pause system
    assert manager.toggle_pause(True) is True
    assert manager.is_system_paused is True

    # Resume system
    assert manager.toggle_pause(False) is False
    assert manager.is_system_paused is False


def test_force_inject_goal(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    manager = HumanInterventionManager(registry=registry)

    goal = manager.force_inject_goal(
        title="Emergency Patch",
        request="Apply security fix immediately",
        target="/src/auth.py",
    )

    assert goal["title"] == "Emergency Patch"
    assert goal["evidence"]["injected_by"] == "operator"


def test_emergency_lockdown():
    policy = CapabilityPolicy({Capability.WRITE_FILES: ExecutionPermission.AUTO_APPROVE})
    manager = HumanInterventionManager(capability_policy=policy)

    # Trigger lockdown
    lockdown_matrix = manager.emergency_lockdown()

    assert lockdown_matrix["DELETE_FILES"] == "DENY"
    assert lockdown_matrix["WRITE_FILES"] == "PROMPT_USER"