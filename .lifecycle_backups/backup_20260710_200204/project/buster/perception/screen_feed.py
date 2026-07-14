from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ScreenPerceptionFeed:
    def __init__(self, data_dir: str | Path = "data", auto_persist: bool = True) -> None:
        self.data_dir = Path(data_dir)
        self.auto_persist = auto_persist
        self.observations: List[Dict[str, Any]] = []
        self.state = {
            "source": "screen",
            "observations": 0,
            "updated": _now(),
        }
        self.state_file = self.data_dir / "screen_perception_feed_state.json"
        self.observations_file = self.data_dir / "screen_perception_feed_observations.json"
        self._persist()

    def observe(
        self,
        observation_type: str = "screen",
        summary: str = "",
        confidence: float = 0.5,
        importance: float = 0.5,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        obs = {
            "id": f"screen_obs_{len(self.observations) + 1}",
            "timestamp": _now(),
            "source": "screen",
            "type": observation_type,
            "summary": summary,
            "confidence": float(confidence),
            "importance": float(importance),
            "data": data or {},
        }
        self.observations.append(obs)
        self.state["observations"] = len(self.observations)
        self.state["last_observation"] = obs
        self.state["updated"] = _now()
        self._persist()
        return obs

    def feed_observation(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.observe(*args, **kwargs)

    def status(self) -> Dict[str, Any]:
        return dict(self.state)

    def _persist(self) -> None:
        if not self.auto_persist:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        self.observations_file.write_text(json.dumps(self.observations, indent=2), encoding="utf-8")
