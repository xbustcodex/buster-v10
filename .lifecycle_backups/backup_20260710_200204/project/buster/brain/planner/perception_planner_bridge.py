from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List
import json


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PerceptionPlannerBridge:
    def __init__(self, data_dir: str | Path = "data", auto_persist: bool = True) -> None:
        self.data_dir = Path(data_dir)
        self.auto_persist = auto_persist
        self.state_file = self.data_dir / "perception_planner_bridge_state.json"
        self.state: Dict[str, Any] = {
            "created": _now(),
            "updated": _now(),
            "plans": 0,
            "last_plan": None,
        }
        self._persist()

    def _load_json_list(self, filename: str) -> List[Dict[str, Any]]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _recent_observations(self) -> List[Dict[str, Any]]:
        observations: List[Dict[str, Any]] = []
        for name in (
            "real_perception_loop_observations.json",
            "vision_perception_feed_observations.json",
            "screen_perception_feed_observations.json",
            "perception_observations.json",
        ):
            observations.extend(self._load_json_list(name))
        return observations[-10:]

    def context_for_planner(self) -> Dict[str, Any]:
        recent = self._recent_observations()
        suggestion = "Observe quietly and wait for a meaningful event."

        summaries = " ".join(str(o.get("summary", "")) for o in recent)
        data_text = " ".join(json.dumps(o.get("data", {})) for o in recent)

        if "ESP32" in summaries or "ESP32" in data_text:
            suggestion = "Prepare ESP32 hardware workflow and make Arduino/serial tools available."
        elif "Android Studio" in summaries or "Android Studio" in data_text:
            suggestion = "Prepare Android development context and monitor project activity."
        elif recent:
            suggestion = "Prepare planner context from recent perception observations."

        return {
            "timestamp": _now(),
            "recent_observations": recent,
            "observation_count": len(recent),
            "suggestion": suggestion,
            "focus": recent[-1].get("summary") if recent else None,
        }

    def create_plan_from_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        importance = float(observation.get("importance", 0.5))
        confidence = float(observation.get("confidence", 0.5))
        summary = observation.get("summary", "")
        source = observation.get("source", "unknown")

        action = "record_observation"
        priority = "normal"

        if importance >= 0.8:
            priority = "high"
            action = "update_world_model_and_notify_companion"
        elif confidence < 0.4:
            priority = "low"
            action = "request_more_context"

        plan = {
            "timestamp": _now(),
            "source": source,
            "summary": summary,
            "priority": priority,
            "action": action,
            "confidence": confidence,
            "importance": importance,
            "steps": [
                "record perception event",
                "update world model",
                "refresh working memory",
            ],
        }

        if priority == "high":
            plan["steps"].append("consider companion speech")

        self.state["plans"] = int(self.state.get("plans", 0)) + 1
        self.state["last_plan"] = plan
        self.state["updated"] = _now()
        self._persist()
        return plan

    def plan_from_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return self.create_plan_from_observation(observation)

    def advise(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return self.create_plan_from_observation(observation)

    def status(self) -> Dict[str, Any]:
        return dict(self.state)

    def _persist(self) -> None:
        if not self.auto_persist:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
