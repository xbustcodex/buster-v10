from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent

def write(path, content):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"[WRITE] {path}")

def create_json(path, data):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        print(f"[SKIP] {path}")
        return
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[CREATE] {path}")

print("=== Applying Buster v5.1 Real Perception Loop Patch ===")

write("buster/perception/sources.py", r'''
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PerceptionSource:
    name: str
    kind: str
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class PerceptionObservation:
    source: str
    observation_type: str
    summary: str
    confidence: float = 0.75
    importance: float = 0.5
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "observation_type": self.observation_type,
            "summary": self.summary,
            "confidence": max(0.0, min(1.0, float(self.confidence))),
            "importance": max(0.0, min(1.0, float(self.importance))),
            "data": self.data,
            "timestamp": self.timestamp,
        }
''')

write("buster/perception/observation_loop.py", r'''
from pathlib import Path
import json
from typing import Any, Dict, List
from .sources import PerceptionObservation, utc_now


class ObservationLoop:
    """Collects observations from camera, screen, projects and hardware.

    This class is intentionally source-agnostic. Real camera/screen modules can feed
    observations into it without the World Model needing to know where they came from.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "perception_observations.json"
        self.state_path = self.data_dir / "real_perception_loop_state.json"
        self._ensure()

    def _ensure(self):
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")
        if not self.state_path.exists():
            self.state_path.write_text(json.dumps({
                "enabled": True,
                "last_tick": None,
                "observations_seen": 0,
                "meaningful_observations": 0,
            }, indent=2), encoding="utf-8")

    def _read_list(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write_list(self, items: List[Dict[str, Any]]):
        self.path.write_text(json.dumps(items[-500:], indent=2), encoding="utf-8")

    def record(self, observation: PerceptionObservation) -> Dict[str, Any]:
        item = observation.to_dict()
        items = self._read_list()
        items.append(item)
        self._write_list(items)
        state = self.status()
        state["last_tick"] = utc_now()
        state["observations_seen"] = int(state.get("observations_seen", 0)) + 1
        if item["importance"] >= 0.65:
            state["meaningful_observations"] = int(state.get("meaningful_observations", 0)) + 1
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return item

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._read_list()[-limit:]

    def status(self) -> Dict[str, Any]:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {"enabled": True, "last_tick": None, "observations_seen": 0, "meaningful_observations": 0}
''')

write("buster/world_model/live_update.py", r'''
from pathlib import Path
import json
from typing import Any, Dict, List
from datetime import datetime, timezone


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WorldModelLiveUpdater:
    """Turns perception observations into World Model facts and relationships."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.world_path = self.data_dir / "world_model.json"
        self.update_path = self.data_dir / "world_model_live_updates.json"
        self._ensure()

    def _ensure(self):
        if not self.world_path.exists():
            self.world_path.write_text(json.dumps({"entities": [], "observations": [], "relationships": []}, indent=2), encoding="utf-8")
        if not self.update_path.exists():
            self.update_path.write_text("[]", encoding="utf-8")

    def _read_world(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.world_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        data.setdefault("entities", [])
        data.setdefault("observations", [])
        data.setdefault("relationships", [])
        return data

    def _write_world(self, data: Dict[str, Any]):
        data["observations"] = data.get("observations", [])[-1000:]
        self.world_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def update_from_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        world = self._read_world()
        obs_record = {
            "id": f"obs_{len(world.get('observations', [])) + 1}",
            "timestamp": observation.get("timestamp") or now(),
            "source": observation.get("source", "unknown"),
            "type": observation.get("observation_type", "general"),
            "summary": observation.get("summary", ""),
            "confidence": observation.get("confidence", 0.75),
            "importance": observation.get("importance", 0.5),
            "data": observation.get("data", {}),
        }
        world["observations"].append(obs_record)

        # Create/update simple entities from detected object/app/device/project fields.
        data = observation.get("data", {}) or {}
        for key in ("object", "app", "device", "project", "person"):
            value = data.get(key)
            if value:
                self._upsert_entity(world, key, str(value), obs_record["id"])

        self._write_world(world)
        update = {
            "timestamp": now(),
            "observation_id": obs_record["id"],
            "summary": obs_record["summary"],
            "world_observations": len(world["observations"]),
            "entities": len(world["entities"]),
        }
        updates = self.recent_updates(999)
        updates.append(update)
        self.update_path.write_text(json.dumps(updates[-500:], indent=2), encoding="utf-8")
        return update

    def _upsert_entity(self, world: Dict[str, Any], kind: str, name: str, obs_id: str):
        for entity in world["entities"]:
            if entity.get("kind") == kind and entity.get("name") == name:
                entity["last_seen"] = now()
                entity["seen_count"] = int(entity.get("seen_count", 0)) + 1
                entity.setdefault("observations", []).append(obs_id)
                entity["observations"] = entity["observations"][-50:]
                return
        world["entities"].append({
            "id": f"entity_{len(world['entities']) + 1}",
            "kind": kind,
            "name": name,
            "first_seen": now(),
            "last_seen": now(),
            "seen_count": 1,
            "observations": [obs_id],
        })

    def recent_updates(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.update_path.read_text(encoding="utf-8"))[-limit:]
        except Exception:
            return []
''')

write("buster/companion/perception_companion.py", r'''
from pathlib import Path
import json
from typing import Any, Dict, Optional
from datetime import datetime, timezone


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PerceptionCompanion:
    """Decides when Buster should speak about perception/world changes."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.queue_path = self.data_dir / "presence_speech_queue.json"
        self.state_path = self.data_dir / "companion_world_state.json"
        self._ensure()

    def _ensure(self):
        if not self.queue_path.exists():
            self.queue_path.write_text("[]", encoding="utf-8")
        if not self.state_path.exists():
            self.state_path.write_text(json.dumps({"mode": "companion", "last_spoken": None}, indent=2), encoding="utf-8")

    def consider(self, observation: Dict[str, Any], world_update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        importance = float(observation.get("importance", 0.5))
        if importance < 0.65:
            return None
        summary = observation.get("summary", "I noticed something useful.")
        message = self._message_for(observation, world_update, summary)
        item = {
            "timestamp": now(),
            "priority": "normal" if importance < 0.85 else "high",
            "reason": "meaningful_perception_observation",
            "message": message,
            "confidence": observation.get("confidence", 0.75),
            "source": observation.get("source", "perception"),
        }
        queue = self.queue(limit=999)
        queue.append(item)
        self.queue_path.write_text(json.dumps(queue[-200:], indent=2), encoding="utf-8")
        return item

    def _message_for(self, observation: Dict[str, Any], world_update: Dict[str, Any], summary: str) -> str:
        data = observation.get("data", {}) or {}
        app = data.get("app")
        device = data.get("device")
        project = data.get("project")
        if app == "Android Studio":
            return "I see Android Studio is active. I can keep an eye on builds and Logcat while you work."
        if device:
            return f"I noticed {device}. I can prepare the right tools if you want to work with it."
        if project:
            return f"I noticed activity on {project}. I can update the project model and watch for useful patterns."
        return f"I noticed this: {summary}"

    def queue(self, limit: int = 20):
        try:
            return json.loads(self.queue_path.read_text(encoding="utf-8"))[-limit:]
        except Exception:
            return []
''')

write("buster/perception/real_perception_loop.py", r'''
from typing import Any, Dict, Optional
from .sources import PerceptionObservation
from .observation_loop import ObservationLoop
from buster.world_model.live_update import WorldModelLiveUpdater
from buster.companion.perception_companion import PerceptionCompanion


class RealPerceptionLoop:
    """Perception -> World Model -> Companion loop."""

    def __init__(self, data_dir: str = "data"):
        self.observations = ObservationLoop(data_dir=data_dir)
        self.world = WorldModelLiveUpdater(data_dir=data_dir)
        self.companion = PerceptionCompanion(data_dir=data_dir)

    def observe(self, source: str, observation_type: str, summary: str, confidence: float = 0.75,
                importance: float = 0.5, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        obs = PerceptionObservation(
            source=source,
            observation_type=observation_type,
            summary=summary,
            confidence=confidence,
            importance=importance,
            data=data or {},
        )
        record = self.observations.record(obs)
        world_update = self.world.update_from_observation(record)
        speech = self.companion.consider(record, world_update)
        return {
            "observation": record,
            "world_update": world_update,
            "speech": speech,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "loop": self.observations.status(),
            "recent_observations": self.observations.recent(5),
            "recent_world_updates": self.world.recent_updates(5),
            "speech_queue": self.companion.queue(5),
        }
''')

write("buster/vision/perception_feed.py", r'''
from typing import Any, Dict, Optional
from buster.perception.real_perception_loop import RealPerceptionLoop


class VisionPerceptionFeed:
    """Adapter for camera/screen observations into the real perception loop."""

    def __init__(self, data_dir: str = "data"):
        self.loop = RealPerceptionLoop(data_dir=data_dir)

    def feed_camera_detection(self, label: str, confidence: float = 0.75, extra: Optional[Dict[str, Any]] = None):
        data = dict(extra or {})
        data.setdefault("object", label)
        return self.loop.observe(
            source="camera",
            observation_type="object_detected",
            summary=f"Camera detected {label}",
            confidence=confidence,
            importance=data.pop("importance", 0.55),
            data=data,
        )

    def feed_screen_context(self, app: str, summary: Optional[str] = None, confidence: float = 0.8,
                            extra: Optional[Dict[str, Any]] = None):
        data = dict(extra or {})
        data.setdefault("app", app)
        return self.loop.observe(
            source="screen",
            observation_type="app_context",
            summary=summary or f"Screen context shows {app}",
            confidence=confidence,
            importance=data.pop("importance", 0.7),
            data=data,
        )
''')

write("buster/perception/__init__.py", r'''
try:
    from .sources import PerceptionObservation, PerceptionSource
    from .observation_loop import ObservationLoop
    from .real_perception_loop import RealPerceptionLoop
except Exception:
    pass
''')

write("buster/workspace/perception_dashboard.py", r'''
from buster.perception.real_perception_loop import RealPerceptionLoop


class PerceptionDashboard:
    def __init__(self, data_dir: str = "data"):
        self.loop = RealPerceptionLoop(data_dir=data_dir)

    def snapshot(self):
        status = self.loop.status()
        return {
            "title": "Real Perception Loop",
            "enabled": status["loop"].get("enabled", True),
            "observations_seen": status["loop"].get("observations_seen", 0),
            "meaningful_observations": status["loop"].get("meaningful_observations", 0),
            "recent_observations": status["recent_observations"],
            "recent_world_updates": status["recent_world_updates"],
            "speech_queue": status["speech_queue"],
        }
''')

write("buster/ui/widgets/perception_loop_widget.py", r'''
try:
    from buster.workspace.perception_dashboard import PerceptionDashboard
except Exception:
    PerceptionDashboard = None


class PerceptionLoopWidgetModel:
    def __init__(self, data_dir: str = "data"):
        self.dashboard = PerceptionDashboard(data_dir=data_dir) if PerceptionDashboard else None

    def data(self):
        if not self.dashboard:
            return {"title": "Real Perception Loop", "enabled": False}
        return self.dashboard.snapshot()
''')

write("buster/brain/planner/perception_planner_bridge.py", r'''
from buster.perception.real_perception_loop import RealPerceptionLoop


class PerceptionPlannerBridge:
    """Lets the planner use what Buster has recently perceived."""

    def __init__(self, data_dir: str = "data"):
        self.loop = RealPerceptionLoop(data_dir=data_dir)

    def context_for_planner(self):
        status = self.loop.status()
        return {
            "recent_observations": status.get("recent_observations", []),
            "recent_world_updates": status.get("recent_world_updates", []),
            "suggestion": self._suggest(status),
        }

    def _suggest(self, status):
        observations = status.get("recent_observations", [])
        for obs in reversed(observations):
            data = obs.get("data", {}) or {}
            if data.get("app") == "Android Studio":
                return "Prepare Android development assistance and monitor builds."
            if data.get("device"):
                return f"Prepare tools for {data.get('device')}."
            if data.get("project"):
                return f"Refresh project intelligence for {data.get('project')}."
        return "No perception-driven action needed."
''')

write("test_v5_1_real_perception_loop.py", r'''
import tempfile
from pathlib import Path

from buster.perception.real_perception_loop import RealPerceptionLoop
from buster.vision.perception_feed import VisionPerceptionFeed
from buster.brain.planner.perception_planner_bridge import PerceptionPlannerBridge
from buster.workspace.perception_dashboard import PerceptionDashboard
from buster.ui.widgets.perception_loop_widget import PerceptionLoopWidgetModel


def test_real_perception_loop():
    with tempfile.TemporaryDirectory() as td:
        loop = RealPerceptionLoop(data_dir=td)
        result = loop.observe(
            source="screen",
            observation_type="app_context",
            summary="Android Studio is active",
            confidence=0.92,
            importance=0.8,
            data={"app": "Android Studio", "project": "Android Toolbox"},
        )
        assert result["observation"]["summary"] == "Android Studio is active"
        assert result["world_update"]["world_observations"] >= 1
        assert result["speech"] is not None
        assert "Android Studio" in result["speech"]["message"]

        feed = VisionPerceptionFeed(data_dir=td)
        feed.feed_camera_detection("ESP32 board", confidence=0.88, extra={"device": "ESP32", "importance": 0.9})

        bridge = PerceptionPlannerBridge(data_dir=td)
        ctx = bridge.context_for_planner()
        assert ctx["recent_observations"]
        assert "Prepare" in ctx["suggestion"]

        dash = PerceptionDashboard(data_dir=td).snapshot()
        assert dash["observations_seen"] >= 2

        widget = PerceptionLoopWidgetModel(data_dir=td).data()
        assert widget["title"] == "Real Perception Loop"


if __name__ == "__main__":
    test_real_perception_loop()
    print("SUCCESS: v5.1 Real Perception Loop tests passed")
''')

create_json("data/perception_observations.json", [])
create_json("data/real_perception_loop_state.json", {
    "enabled": True,
    "last_tick": None,
    "observations_seen": 0,
    "meaningful_observations": 0,
})
create_json("data/world_model_live_updates.json", [])

print("\nSUCCESS: Buster v5.1 Real Perception Loop installed.")
print("Next: python test_v5_1_real_perception_loop.py")
