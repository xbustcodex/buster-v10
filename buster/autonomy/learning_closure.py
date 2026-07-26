# buster/autonomy/learning_closure.py
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from buster.autonomy.mission_state import Mission
from buster.memory.context_indexer import LocalRAGIndexer

logger = logging.getLogger(__name__)


@dataclass
class MissionExperienceSummary:
    mission_id: str
    objective: str
    successful_strategies: List[str]
    encountered_failures: List[str]
    solving_agents: List[str]
    learning_score: float
    timestamp: str


class LearningClosureManager:
    """Summarizes completed missions and feeds structured experience records into local RAG memory."""

    def __init__(self, experience_storage_dir: str | Path = "data/experiences", rag_indexer: Optional[LocalRAGIndexer] = None) -> None:
        self.storage_dir = Path(experience_storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.rag_indexer = rag_indexer

    def record_learning(
        self,
        mission: Mission,
        successful_strategies: List[str],
        encountered_failures: List[str],
        solving_agents: List[str],
        learning_score: float = 0.95,
    ) -> MissionExperienceSummary:
        import datetime
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

        summary = MissionExperienceSummary(
            mission_id=mission.mission_id,
            objective=mission.objective,
            successful_strategies=successful_strategies,
            encountered_failures=encountered_failures,
            solving_agents=solving_agents,
            learning_score=learning_score,
            timestamp=timestamp,
        )

        # Save record to disk
        exp_path = self.storage_dir / f"{mission.mission_id}_experience.json"
        exp_path.write_text(json.dumps(summary.__dict__, indent=2), encoding="utf-8")
        logger.info(f"Recorded experience summary for completed mission [{mission.mission_id}]")

        # Feed back into local RAG index if available
        if self.rag_indexer:
            rag_content = (
                f"Mission ID: {mission.mission_id}. "
                f"Mission Objective: {mission.objective}. "
                f"Successful Strategies: {', '.join(successful_strategies)}. "
                f"Resolved Failures: {', '.join(encountered_failures)}. "
                f"Solving Agents: {', '.join(solving_agents)}."
            )
            self.rag_indexer.add_document(
                source_file=f"experience_{mission.mission_id}.md",
                text=rag_content,
                metadata={"type": "mission_experience", "mission_id": mission.mission_id},
            )
            logger.info(f"Indexed mission [{mission.mission_id}] experience into local RAG memory.")

        return summary