# buster/memory/context_indexer.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    chunk_id: str
    source_file: str
    content: str
    metadata: Dict[str, Any]


class LocalRAGIndexer:
    """Provides local document ingestion, chunking, and lightweight keyword-similarity retrieval for Buster's memory."""

    def __init__(self, index_storage_path: str | Path = "data/memory_index.json") -> None:
        self.storage_path = Path(index_storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.chunks: Dict[str, DocumentChunk] = {}
        self.load_index()

    def load_index(self) -> None:
        """Loads existing index from disk if available."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for cid, cdata in data.items():
                    self.chunks[cid] = DocumentChunk(**cdata)
                logger.info(f"Loaded {len(self.chunks)} chunks into local RAG index.")
            except Exception as e:
                logger.error(f"Failed to load vector index: {e}")

    def save_index(self) -> None:
        """Saves current chunks to disk."""
        data = {cid: asdict(chunk) for cid, chunk in self.chunks.items()}
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_document(self, source_file: str, text: str, metadata: Optional[Dict[str, Any]] = None, chunk_size: int = 300) -> int:
        """Ingests a document, splits it into chunks, and indexes them."""
        meta = metadata or {}
        words = text.split()
        added_count = 0

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk_content = " ".join(chunk_words)
            chunk_id = f"chk_{abs(hash(source_file + chunk_content))}"
            
            self.chunks[chunk_id] = DocumentChunk(
                chunk_id=chunk_id,
                source_file=source_file,
                content=chunk_content,
                metadata=meta,
            )
            added_count += 1

        self.save_index()
        logger.info(f"Indexed {added_count} chunks from [{source_file}]")
        return added_count

    def search(self, query: str, top_k: int = 3) -> List[DocumentChunk]:
        """Performs robust token-overlap similarity search with stem/substring tolerance."""
        query_tokens = {word.strip(".,!?").lower() for word in query.split()}
        if not query_tokens or not self.chunks:
            return []

        scored_chunks = []
        for chunk in self.chunks.values():
            chunk_text_lower = chunk.content.lower()
            chunk_tokens = {word.strip(".,!?").lower() for word in chunk.content.split()}
            
            # Calculate overlap score
            intersection = query_tokens.intersection(chunk_tokens)
            score = len(intersection) / max(len(query_tokens), 1)

            # Boost score if key query roots appear as substrings
            for q_tok in query_tokens:
                if len(q_tok) > 3 and q_tok in chunk_text_lower:
                    score += 0.2

            if score > 0:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_chunks[:top_k]]