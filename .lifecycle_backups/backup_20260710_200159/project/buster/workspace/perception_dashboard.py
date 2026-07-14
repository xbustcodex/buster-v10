from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List
import json


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PerceptionDashboard:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)

    def _load_json_list(self, filename: str) -> List[Dict[str, Any]]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def observations(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for name in (
            "real_perception_loop_observations.json",
            "vision_perception_feed_observations.json",
            "screen_perception_feed_observations.json",
            "perception_observations.json",
        ):
            items.extend(self._load_json_list(name))
        return items

    def snapshot(self) -> Dict[str, Any]:
        obs = self.observations()
        return {
            "title": "Perception Dashboard",
            "updated": _now(),
            "observations_seen": len(obs),
            "recent_observations": obs[-10:],
            "last_observation": obs[-1] if obs else None,
        }
