"""
Test v13.1: Persistent Goal Registry & Cooldown Management
"""
import pytest
import time
from pathlib import Path
from buster.autonomy.goals.models import GoalProposal
from buster.autonomy.goals.registry import GoalRegistry
from buster.autonomy.goals.storage import GoalStorage


def test_goal_registry_persistence_and_cooldown(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    storage = GoalStorage(storage_path=storage_path)
    registry = GoalRegistry(storage=storage)

    # 1. Create and register proposal
    proposal = GoalProposal(
        title="Check system logs",
        request="Scan logs for errors",
        target="/var/log/system.log",
        signal_id="sig_123",
    )
    goal_data = registry.register_proposal(proposal, evidence={"log_size_mb": 50})

    assert goal_data["id"] == proposal.id
    assert storage_path.exists()

    # 2. Update status and verify execution timestamp
    registry.update_status(proposal.id, "COMPLETED", result={"errors_found": 0})
    
    # 3. Check cooldown logic prevents duplicate goal generation
    assert registry.is_on_cooldown("/var/log/system.log", cooldown_seconds=60.0) is True
    assert registry.is_on_cooldown("/var/log/other.log", cooldown_seconds=60.0) is False

    # 4. Reload from disk into a fresh registry instance to prove persistence
    fresh_registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    loaded_goal = fresh_registry.get(proposal.id)

    assert loaded_goal is not None
    assert loaded_goal["status"] == "COMPLETED"
    assert loaded_goal["evidence"]["log_size_mb"] == 50