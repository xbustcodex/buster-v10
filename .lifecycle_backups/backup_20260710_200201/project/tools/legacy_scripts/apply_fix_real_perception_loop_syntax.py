from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "buster" / "perception" / "real_perception_loop.py"

CODE = """from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RealPerceptionLoop:
    # Practical bridge between perception inputs and Buster's World Model / Companion systems.

    def __init__(
        self,
        data_dir: str | Path = "data",
        auto_persist: bool = True,
        mode: str = "companion",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.auto_persist = auto_persist
        self.mode = mode
        self.running = False
        self.observations: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {
            "running": False,
            "mode": mode,
            "started_at": None,
            "stopped_at": None,
            "last_observation": None,
            "observation_count": 0,
            "updated": _now(),
        }

        self.state_file = self.data_dir / "real_perception_loop_state.json"
        self.observations_file = self.data_dir / "real_perception_loop_observations.json"

        if self.auto_persist:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._persist()

    def start(self) -> Dict[str, Any]:
        self.running = True
        self.state["running"] = True
        self.state["started_at"] = self.state.get("started_at") or _now()
        self.state["stopped_at"] = None
        self.state["updated"] = _now()
        self._persist()
        return dict(self.state)

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.state["running"] = False
        self.state["stopped_at"] = _now()
        self.state["updated"] = _now()
        self._persist()
        return dict(self.state)

    def status(self) -> Dict[str, Any]:
        return dict(self.state)

    def observe(
        self,
        source: str,
        observation_type: str | None = None,
        summary: str = "",
        confidence: float = 0.5,
        importance: float = 0.5,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if observation_type is None:
            observation_type = kwargs.pop("type", None) or kwargs.pop("kind", None) or "observation"

        observation = {
            "id": f"obs_{len(self.observations) + 1}",
            "timestamp": _now(),
            "source": source,
            "type": observation_type,
            "summary": summary,
            "confidence": float(confidence),
            "importance": float(importance),
            "data": data or {},
        }

        self.observations.append(observation)
        self.state["last_observation"] = observation
        self.state["observation_count"] = len(self.observations)
        self.state["updated"] = _now()

        world_update = self._update_world_model(observation)
        companion_update = self._update_companion_state(observation, world_update)
        speech = self._maybe_generate_speech(observation, world_update)

        result = {
            "ok": True,
            "observation": observation,
            "world_update": world_update,
            "companion_update": companion_update,
            "speech": speech,
            "state": dict(self.state),
        }

        self._persist()
        return result

    def tick(self) -> Dict[str, Any]:
        self.state["updated"] = _now()
        self._persist()
        return {
            "ok": True,
            "running": self.running,
            "state": dict(self.state),
        }

    def _update_world_model(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "updated": _now(),
            "world_observations": len(self.observations),
            "last_source": observation["source"],
            "last_type": observation["type"],
            "last_summary": observation["summary"],
            "confidence": observation["confidence"],
            "importance": observation["importance"],
        }

    def _update_companion_state(
        self,
        observation: Dict[str, Any],
        world_update: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = "observing"
        if observation["importance"] >= 0.8:
            state = "attentive"
        if observation["confidence"] < 0.4:
            state = "uncertain"

        return {
            "updated": _now(),
            "state": state,
            "focus": observation["summary"],
            "source": observation["source"],
            "world_observations": world_update["world_observations"],
        }

    def _maybe_generate_speech(
        self,
        observation: Dict[str, Any],
        world_update: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if observation["importance"] < 0.7:
            return None

        text = f"I noticed: {observation['summary']}"
        if observation["source"] == "screen" and "Android Studio" in observation["summary"]:
            text = "I see Android Studio is active. I can monitor the project context."

        return {
            "timestamp": _now(),
            "reason": "high_importance_observation",
            "text": text,
            "confidence": observation["confidence"],
            "importance": observation["importance"],
        }

    def _persist(self) -> None:
        if not self.auto_persist:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        self.observations_file.write_text(json.dumps(self.observations, indent=2), encoding="utf-8")
"""

def main() -> None:
    print("=== Applying RealPerceptionLoop Syntax Repair ===")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(CODE, encoding="utf-8")
    print(f"[WRITE] {TARGET.relative_to(ROOT)}")
    print("\nSUCCESS: Syntax repaired.")
    print("Next: python -m pytest")

if __name__ == "__main__":
    main()
