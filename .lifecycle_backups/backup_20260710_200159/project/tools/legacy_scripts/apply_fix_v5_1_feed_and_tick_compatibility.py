from pathlib import Path

ROOT = Path(__file__).resolve().parent

REAL_LOOP = ROOT / "buster" / "perception" / "real_perception_loop.py"
VISION_FEED = ROOT / "buster" / "vision" / "perception_feed.py"
SCREEN_FEED = ROOT / "buster" / "perception" / "screen_feed.py"

def patch_real_loop() -> None:
    text = REAL_LOOP.read_text(encoding="utf-8")

    text = text.replace(
        '"observation_count": 0,\n            "updated": _now(),',
        '"observation_count": 0,\n            "tick": 0,\n            "updated": _now(),'
    )

    start = text.find("    def tick(self) -> Dict[str, Any]:")
    if start != -1:
        end = text.find("\n    def _update_world_model", start)
        if end != -1:
            new_tick = '''    def tick(self) -> Dict[str, Any]:
        self.state["tick"] = int(self.state.get("tick", 0)) + 1
        self.state["updated"] = _now()
        self._persist()
        return {
            "ok": True,
            "tick": self.state["tick"],
            "running": self.running,
            "state": dict(self.state),
        }

'''
            text = text[:start] + new_tick + text[end+1:]

    REAL_LOOP.write_text(text, encoding="utf-8")

def write_vision_feed() -> None:
    VISION_FEED.parent.mkdir(parents=True, exist_ok=True)
    VISION_FEED.write_text('''from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class VisionPerceptionFeed:
    def __init__(self, data_dir: str | Path = "data", auto_persist: bool = True) -> None:
        self.data_dir = Path(data_dir)
        self.auto_persist = auto_persist
        self.observations: List[Dict[str, Any]] = []
        self.state = {
            "source": "vision",
            "observations": 0,
            "updated": _now(),
        }
        self.state_file = self.data_dir / "vision_perception_feed_state.json"
        self.observations_file = self.data_dir / "vision_perception_feed_observations.json"
        self._persist()

    def observe(
        self,
        observation_type: str = "vision",
        summary: str = "",
        confidence: float = 0.5,
        importance: float = 0.5,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        obs = {
            "id": f"vision_obs_{len(self.observations) + 1}",
            "timestamp": _now(),
            "source": "vision",
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

    def snapshot(self, summary: str = "Vision snapshot", **kwargs: Any) -> Dict[str, Any]:
        return self.observe("snapshot", summary, **kwargs)

    def status(self) -> Dict[str, Any]:
        return dict(self.state)

    def _persist(self) -> None:
        if not self.auto_persist:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        self.observations_file.write_text(json.dumps(self.observations, indent=2), encoding="utf-8")
''', encoding="utf-8")

def write_screen_feed() -> None:
    SCREEN_FEED.parent.mkdir(parents=True, exist_ok=True)
    SCREEN_FEED.write_text('''from __future__ import annotations

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
''', encoding="utf-8")

def main() -> None:
    print("=== Applying v5.1 Feed + Tick Compatibility Repair ===")
    patch_real_loop()
    write_vision_feed()
    write_screen_feed()
    print(f"[WRITE] {REAL_LOOP.relative_to(ROOT)}")
    print(f"[WRITE] {VISION_FEED.relative_to(ROOT)}")
    print(f"[WRITE] {SCREEN_FEED.relative_to(ROOT)}")
    print("\\nSUCCESS: Vision feed data_dir and RealPerceptionLoop tick compatibility repaired.")
    print("Next: python -m pytest")

if __name__ == "__main__":
    main()
