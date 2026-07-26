# buster/autonomy/observation_engine.py
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Observation:
    observation_id: str
    mission_id: str
    source: str
    type: str  # e.g., "test.failed", "task.completed", "file.changed"
    importance: float  # 0.0 to 1.0
    requires_replan: bool
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


class ObservationEngine:
    """Collects raw events, normalizes them into Observations, and filters out noise."""

    def __init__(self, importance_threshold: float = 0.3) -> None:
        self.importance_threshold = importance_threshold
        self.observation_history: List[Observation] = []

    def create_observation(
        self,
        mission_id: str,
        source: str,
        obs_type: str,
        importance: float,
        requires_replan: bool,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        obs_id = f"obs_{int(datetime.now(timezone.utc).timestamp())}_{abs(hash(source + obs_type))}"
        observation = Observation(
            observation_id=obs_id,
            mission_id=mission_id,
            source=source,
            type=obs_type,
            importance=importance,
            requires_replan=requires_replan,
            payload=payload or {},
        )
        self.observation_history.append(observation)
        logger.info(f"Recorded observation [{obs_type}] from [{source}] with importance {importance}")
        return observation

    def filter_observations(self, observations: List[Observation]) -> List[Observation]:
        """Deterministic filter to discard low-importance noise."""
        filtered = [obs for obs in observations if obs.importance >= self.importance_threshold]
        logger.debug(f"Filtered {len(observations)} observations down to {len(filtered)} actionable events.")
        return filtered