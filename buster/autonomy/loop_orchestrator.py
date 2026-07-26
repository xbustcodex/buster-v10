# buster/autonomy/loop_orchestrator.py
from __future__ import annotations

import logging
from typing import List, Optional

from buster.autonomy.mission_state import Mission
from buster.autonomy.observation_engine import ObservationEngine, Observation
from buster.autonomy.next_action_selector import NextActionSelector, ActionDecision
from buster.memory.context_indexer import LocalRAGIndexer

logger = logging.getLogger(__name__)


class AutonomousLoopOrchestrator:
    """Coordinates the continuous observe-retrieve-plan-execute-verify autonomy loop for missions."""

    def __init__(self, observation_engine: ObservationEngine, action_selector: NextActionSelector, rag_indexer: Optional[LocalRAGIndexer] = None) -> None:
        self.observation_engine = observation_engine
        self.action_selector = action_selector
        self.rag_indexer = rag_indexer

    def process_mission_tick(self, mission: Mission, raw_event_source: str, event_type: str, event_payload: Optional[dict] = None) -> tuple[Observation, ActionDecision, List[str]]:
        """Executes a single tick of the autonomous loop for a mission."""
        logger.info(f"Orchestrator ticking mission [{mission.mission_id}] with event [{event_type}]")

        # 1. Observe & Normalize
        importance = 0.9 if "failed" in event_type or "denied" in event_type else 0.5
        requires_replan = "failed" in event_type
        
        observation = self.observation_engine.create_observation(
            mission_id=mission.mission_id,
            source=raw_event_source,
            obs_type=event_type,
            importance=importance,
            requires_replan=requires_replan,
            payload=event_payload,
        )

        # 2. Retrieve Relevant Context (RAG) if indexer is available
        retrieved_contexts: List[str] = []
        if self.rag_indexer:
            query = f"{mission.objective} {event_type}"
            chunks = self.rag_indexer.search(query, top_k=2)
            retrieved_contexts = [chunk.content for chunk in chunks]
            logger.info(f"Retrieved {len(retrieved_contexts)} context snippets for mission tick.")

        # 3. Select Next Action
        decision = self.action_selector.select_next_action(mission, observation)

        # 4. Update Mission Stage / Status based on decision
        if decision.action_type == "delegate_fixer":
            mission.current_stage = "RECOVERING"
            mission.status = "RECOVERING"
        elif decision.action_type == "request_approval":
            mission.current_stage = "BLOCKED"
            mission.status = "BLOCKED"
            mission.intervention_required = True
        elif decision.action_type == "complete_mission":
            mission.current_stage = "COMPLETED"
            mission.status = "COMPLETED"

        return observation, decision, retrieved_contexts