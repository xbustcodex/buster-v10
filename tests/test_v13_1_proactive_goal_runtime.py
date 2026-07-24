"""
Test v13 Phase 1: Proactive Intelligence & Autonomous Goal Runtime
"""
import pytest
from pathlib import Path
from buster.runtime import create_runtime_core


def test_proactive_goal_end_to_end(tmp_path):
    # Setup project directory with a stale index marker
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    index_file = project_dir / ".buster_index.json"
    
    # 1. Initialize Runtime
    runtime = create_runtime_core(root=project_dir)
    runtime.start()

    goal_service = runtime.service("goal_service")
    assert goal_service is not None

    # 2. Simulate detection / emit curiosity signal
    signal = goal_service.observe_and_signal(
        signal_type="stale_project_index",
        target=str(index_file),
        metadata={"age_hours": 48}
    )
    assert signal is not None

    # 3. Generate Goal Proposal
    proposal = goal_service.propose_goal_from_signal(signal)
    assert proposal.title == "Rebuild stale project index"

    # 4. Evaluate & Apply Approval Policy
    evaluation = goal_service.evaluate_proposal(proposal)
    assert evaluation.risk_score < 0.2  # Low risk
    assert evaluation.is_approved is True

    # 5. Submit approved goal to execution pipeline (StrategyPlanner -> Sandbox -> Verification -> Learning)
    result = goal_service.execute_approved_goal(proposal)

    # 6. Validate end result
    assert result.success is True
    assert goal_service.get_goal_status(proposal.id) == "COMPLETED"
    assert index_file.exists() or (project_dir / ".buster_index.json").exists()

    runtime.stop()