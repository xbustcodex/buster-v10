# buster/autonomy/loop_checkpoint.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from buster.autonomy.mission_state import Mission, AutonomyPolicy

logger = logging.getLogger(__name__)


@dataclass
class MissionCheckpoint:
    checkpoint_id: str
    mission_id: str
    timestamp: str
    mission_data: Dict[str, Any]
    active_leases: List[str]
    circuit_states: Dict[str, str]


class MissionCheckpointManager:
    """Manages writing and recovering durable checkpoints for missions across runtime restarts."""

    def __init__(self, storage_dir: str | Path = "data/checkpoints") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, mission: Mission, active_leases: Optional[List[str]] = None, circuit_states: Optional[Dict[str, str]] = None) -> MissionCheckpoint:
        """Writes a durable checkpoint for the given mission."""
        import datetime
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        chk_id = f"chk_{mission.mission_id}_{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"
        
        mission.checkpoint_id = chk_id
        
        checkpoint = MissionCheckpoint(
            checkpoint_id=chk_id,
            mission_id=mission.mission_id,
            timestamp=timestamp,
            mission_data=asdict(mission),
            active_leases=active_leases or [],
            circuit_states=circuit_states or {},
        )

        chk_path = self.storage_dir / f"{mission.mission_id}.json"
        chk_path.write_text(json.dumps(asdict(checkpoint), indent=2), encoding="utf-8")
        logger.info(f"Saved durable checkpoint [{chk_id}] for mission [{mission.mission_id}]")
        return checkpoint

    def load_checkpoint(self, mission_id: str) -> Optional[MissionCheckpoint]:
        """Loads the latest checkpoint for a mission if available."""
        chk_path = self.storage_dir / f"{mission_id}.json"
        if not chk_path.exists():
            return None
        try:
            data = json.loads(chk_path.read_text(encoding="utf-8"))
            return MissionCheckpoint(**data)
        except Exception as e:
            logger.error(f"Failed to load checkpoint for mission {mission_id}: {e}")
            return None

    def recover_mission(self, mission_id: str) -> Optional[Mission]:
        """Reconstructs a Mission object from its latest durable checkpoint."""
        checkpoint = self.load_checkpoint(mission_id)
        if not checkpoint:
            return None

        m_data = checkpoint.mission_data
        policy_data = m_data.pop("autonomy_policy", None)
        policy = AutonomyPolicy(**policy_data) if policy_data else None

        mission = Mission(**m_data, autonomy_policy=policy)
        logger.info(f"Successfully recovered mission [{mission_id}] from checkpoint [{checkpoint.checkpoint_id}]")
        return mission