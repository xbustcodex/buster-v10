# tests/test_v30_orchestrator.py
import pytest
from buster.autonomy.mission_state import Mission
from buster.autonomy.observation_engine import ObservationEngine
from buster.autonomy.next_action_selector import NextActionSelector
from buster.autonomy.loop_orchestrator import AutonomousLoopOrchestrator
from buster.memory.context_indexer import LocalRAGIndexer


def test_loop_retrieves_context_before_planning(tmp_path):
    index_file = tmp_path / "rag_index.json"
    indexer = LocalRAGIndexer(index_storage_path=index_file)
    indexer.add_document("architecture.md", "Buster uses autonomous background daemons for execution.")

    obs_engine = ObservationEngine()
    selector = NextActionSelector()
    orchestrator = AutonomousLoopOrchestrator(observation_engine=obs_engine, action_selector=selector, rag_indexer=indexer)

    mission = Mission(
        mission_id="m_orch_1",
        objective="Build daemon feature",
        status="EXECUTING",
        priority=1,
        created_at="2026-07-26T04:00:00Z",
        current_stage="EXECUTING",
    )

    observation, decision, contexts = orchestrator.process_mission_tick(
        mission=mission,
        raw_event_source="tester",
        event_type="test.failed",
        event_payload={"error": "AssertionError"},
    )

    assert observation.type == "test.failed"
    assert decision.action_type == "delegate_fixer"
    assert len(contexts) == 1
    assert "autonomous background daemons" in contexts[0]
    assert mission.status == "RECOVERING"