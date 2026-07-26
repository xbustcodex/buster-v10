# tests/test_v30_e2e_mission.py
import pytest
from buster.autonomy.mission_state import Mission, AutonomyPolicy
from buster.autonomy.observation_engine import ObservationEngine
from buster.autonomy.next_action_selector import NextActionSelector
from buster.autonomy.loop_orchestrator import AutonomousLoopOrchestrator
from buster.autonomy.loop_checkpoint import MissionCheckpointManager
from buster.autonomy.completion_evaluator import CompletionEvaluator, VerificationEvidence
from buster.autonomy.learning_closure import LearningClosureManager
from buster.memory.context_indexer import LocalRAGIndexer


def test_full_autonomous_mission_lifecycle(tmp_path):
    # Setup storage directories and RAG index
    rag_index_file = tmp_path / "rag_index.json"
    indexer = LocalRAGIndexer(index_storage_path=rag_index_file)
    indexer.add_document("runtime_guide.md", "Buster runs autonomous background missions with resilient worker leases.")

    checkpoint_dir = tmp_path / "checkpoints"
    experience_dir = tmp_path / "experiences"

    obs_engine = ObservationEngine()
    selector = NextActionSelector()
    orchestrator = AutonomousLoopOrchestrator(observation_engine=obs_engine, action_selector=selector, rag_indexer=indexer)
    chk_manager = MissionCheckpointManager(storage_dir=checkpoint_dir)
    completion_evaluator = CompletionEvaluator()
    learning_manager = LearningClosureManager(experience_storage_dir=experience_dir, rag_indexer=indexer)

    # 1. Create Mission with Policy & Trace
    policy = AutonomyPolicy(
        level=2,
        allow_file_writes=True,
        allow_shell_commands=True,
        allow_network_access=False,
        allow_process_control=False,
        allow_self_patch=False,
        require_approval_for_merge=True,
        maximum_runtime_minutes=60,
        maximum_child_tasks=10,
    )
    mission = Mission(
        mission_id="m_e2e_01",
        objective="Deploy resilient worker feature",
        status="CREATED",
        priority=1,
        created_at="2026-07-26T04:15:00Z",
        current_stage="INITIALIZATION",
        success_criteria=["All tests pass successfully"],
        trace_id="trace_e2e_xyz",
        autonomy_policy=policy,
    )

    # 2. Process mission tick & retrieve RAG context
    observation, decision, contexts = orchestrator.process_mission_tick(
        mission=mission,
        raw_event_source="tester",
        event_type="test.failed",
        event_payload={"error": "AssertionError: worker lease timeout"},
    )

    assert observation.type == "test.failed"
    assert decision.action_type == "delegate_fixer"
    assert len(contexts) >= 1
    assert "resilient worker leases" in contexts[0]

    # 3. Checkpoint mission state (Simulating persistence before restart)
    chk = chk_manager.save_checkpoint(mission, active_leases=["worker_node_1"], circuit_states={"api": "CLOSED"})
    assert chk.checkpoint_id is not None

    # 4. Simulate Runtime Restart & Recovery
    recovered_mission = chk_manager.recover_mission("m_e2e_01")
    assert recovered_mission is not None
    assert recovered_mission.status == "RECOVERING"
    assert recovered_mission.autonomy_policy.level == 2

    # 5. Evaluate Completion Evidence
    evidence = VerificationEvidence(
        acceptance_criteria_satisfied=True,
        tests_passed=True,
        verification_report_passed=True,
        active_leases_count=0,
        unresolved_critical_failures=False,
        pending_approval=False,
    )
    completion_decision = completion_evaluator.evaluate(recovered_mission, evidence)
    assert completion_decision.status == "COMPLETE"
    recovered_mission.status = "COMPLETED"

    # 6. Record Learning Closure & Feed RAG Index
    summary = learning_manager.record_learning(
        mission=recovered_mission,
        successful_strategies=["Focused context injection", "Worker lease reclamation"],
        encountered_failures=["Test timeout"],
        solving_agents=["BuilderAgent", "FixerAgent"],
        learning_score=0.99,
    )
    assert summary.learning_score == 0.99

    # 7. Verify future RAG retrieval includes past mission experience
    future_search = indexer.search("Worker lease reclamation", top_k=1)
    assert len(future_search) == 1
    assert "m_e2e_01" in future_search[0].content