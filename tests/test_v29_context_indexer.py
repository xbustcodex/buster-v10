# tests/test_v29_context_indexer.py
import pytest
from buster.memory.context_indexer import LocalRAGIndexer


def test_local_rag_indexer(tmp_path):
    index_file = tmp_path / "test_index.json"
    indexer = LocalRAGIndexer(index_storage_path=index_file)

    # Ingest mock documentation / memory log
    indexer.add_document(
        source_file="repair_history.md",
        text="The Windows shell executor encountered timeout errors when PowerShell commands took longer than 30 seconds. Fixed by adding configurable timeout parameters.",
        metadata={"category": "repair"},
    )
    
    indexer.add_document(
        source_file="architecture.md",
        text="Buster uses a WebSocket task bridge and a communication center for multi-node mesh synchronization across desktop and mobile devices.",
        metadata={"category": "architecture"},
    )

    # Search for relevant context
    results = indexer.search("PowerShell timeout errors", top_k=1)

    assert len(results) == 1
    assert "timeout errors" in results[0].content
    assert results[0].source_file == "repair_history.md"