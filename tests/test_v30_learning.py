# tests/test_v30_learning.py
import pytest
from buster.autonomy.mission_state import Mission
from buster.autonomy.learning_closure import LearningClosureManager
from buster.memory.context_indexer import LocalRAGIndexer


def test_completed_mission_generates_learning_record(tmp_path):
    rag_index_file = tmp_path / "rag_index.json"
    indexer = LocalRAGIndexer(index_storage_path=rag_index_file)
    learning_dir = tmp_path / "experiences"

    manager = LearningClosureManager(experience_storage_dir=learning_dir, rag_indexer=indexer)

    mission = Mission(
        mission_id="m_learn_1",
        objective="Implement RAG memory subsystem",
        status="COMPLETED",
        priority=1,
        created_at="2026-07-26T04:08:00Z",
        current_stage="COMPLETED",
    )

    summary = manager.record_learning(
        mission=mission,
        successful_strategies=["Token-overlap Jaccard indexing", "Incremental chunk storage"],
        encountered_failures=["Pluralization token mismatch"],
        solving_agents=["BuilderAgent", "FixerAgent"],
        learning_score=0.98,
    )

    assert summary.mission_id == "m_learn_1"
    assert summary.learning_score == 0.98

    # Verify indexed in local RAG
    results = indexer.search("Token-overlap Jaccard indexing", top_k=1)
    assert len(results) == 1
    assert "m_learn_1" in results[0].content or "RAG memory" in results[0].content