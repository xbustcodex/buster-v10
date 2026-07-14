from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent

FILES = {}

def w(path, text):
    FILES[path] = text.strip() + "\n"

w('buster/world_model/__init__.py', r'''
from .engine import WorldModelEngine
from .entities import WorldEntity
from .observations import Observation
from .relationships import Relationship

__all__ = ["WorldModelEngine", "WorldEntity", "Observation", "Relationship"]
''')

w('buster/world_model/entities.py', r'''
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

@dataclass
class WorldEntity:
    kind: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    confidence: float = 0.75
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def update(self, **attrs):
        self.attributes.update(attrs)
        self.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return self

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return WorldEntity(**data)
''')

w('buster/world_model/observations.py', r'''
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

@dataclass
class Observation:
    source: str
    summary: str
    context: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    confidence: float = 0.75
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return Observation(**data)
''')

w('buster/world_model/relationships.py', r'''
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import uuid

@dataclass
class Relationship:
    source_id: str
    target_id: str
    relation: str
    confidence: float = 0.75
    relationship_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return Relationship(**data)
''')

w('buster/world_model/storage.py', r'''
from pathlib import Path
import json

class WorldModelStorage:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.path = self.data_dir / "world_model.json"

    def load(self):
        if not self.path.exists():
            return {"entities": [], "observations": [], "relationships": [], "timeline": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"entities": [], "observations": [], "relationships": [], "timeline": []}

    def save(self, state):
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state
''')

w('buster/world_model/memory.py', r'''
class WorldMemory:
    def __init__(self):
        self.short_term = []
        self.episodic = []
        self.semantic = []

    def remember_short_term(self, item):
        self.short_term.append(item)
        self.short_term = self.short_term[-100:]
        return item

    def remember_episode(self, item):
        self.episodic.append(item)
        self.episodic = self.episodic[-500:]
        return item

    def remember_semantic(self, item):
        self.semantic.append(item)
        self.semantic = self.semantic[-500:]
        return item

    def snapshot(self):
        return {
            "short_term": list(self.short_term),
            "episodic": list(self.episodic),
            "semantic": list(self.semantic),
        }
''')

w('buster/world_model/understanding.py', r'''
class UnderstandingEngine:
    def infer_context(self, observations):
        text = " ".join(o.get("summary", "") if isinstance(o, dict) else getattr(o, "summary", "") for o in observations).lower()
        context = {"mode": "idle", "signals": []}
        if "android studio" in text or "gradle" in text or "logcat" in text:
            context["mode"] = "android_development"
            context["signals"].append("android_workflow")
        if "esp32" in text or "arduino" in text:
            context["mode"] = "hardware_development"
            context["signals"].append("hardware_workflow")
        if "error" in text or "failed" in text or "crash" in text:
            context["signals"].append("needs_attention")
        return context

    def recommend(self, context):
        mode = context.get("mode")
        if mode == "android_development":
            return "Prepare Android tooling, monitor builds, and watch Logcat for errors."
        if mode == "hardware_development":
            return "Prepare hardware plugins and watch serial/device connection status."
        if "needs_attention" in context.get("signals", []):
            return "Create a mission for diagnosis and route it through Tester, Fixer, and Verifier."
        return "Stay present, observe quietly, and avoid interrupting unless something meaningful changes."
''')

w('buster/world_model/engine.py', r'''
from datetime import datetime, timezone
from .storage import WorldModelStorage
from .entities import WorldEntity
from .observations import Observation
from .relationships import Relationship
from .memory import WorldMemory
from .understanding import UnderstandingEngine

class WorldModelEngine:
    def __init__(self, data_dir="data"):
        self.storage = WorldModelStorage(data_dir)
        self.state = self.storage.load()
        self.memory = WorldMemory()
        self.understanding = UnderstandingEngine()

    def add_entity(self, kind, name, attributes=None, confidence=0.75):
        entity = WorldEntity(kind=kind, name=name, attributes=attributes or {}, confidence=confidence)
        self.state.setdefault("entities", []).append(entity.to_dict())
        self._timeline("entity_added", f"{kind}: {name}", confidence)
        self.storage.save(self.state)
        return entity.to_dict()

    def observe(self, source, summary, context=None, importance=0.5, confidence=0.75):
        obs = Observation(source=source, summary=summary, context=context or {}, importance=importance, confidence=confidence)
        data = obs.to_dict()
        self.state.setdefault("observations", []).append(data)
        self.memory.remember_short_term(data)
        if importance >= 0.7:
            self.memory.remember_episode(data)
        self._timeline("observation", summary, confidence)
        self.storage.save(self.state)
        return data

    def link(self, source_id, target_id, relation, confidence=0.75):
        rel = Relationship(source_id=source_id, target_id=target_id, relation=relation, confidence=confidence)
        self.state.setdefault("relationships", []).append(rel.to_dict())
        self._timeline("relationship", relation, confidence)
        self.storage.save(self.state)
        return rel.to_dict()

    def understand_now(self):
        recent = self.state.get("observations", [])[-20:]
        context = self.understanding.infer_context(recent)
        recommendation = self.understanding.recommend(context)
        snapshot = {
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "context": context,
            "recommendation": recommendation,
            "entity_count": len(self.state.get("entities", [])),
            "observation_count": len(self.state.get("observations", [])),
            "relationship_count": len(self.state.get("relationships", [])),
        }
        self.state["current_understanding"] = snapshot
        self.storage.save(self.state)
        return snapshot

    def _timeline(self, event_type, summary, confidence):
        self.state.setdefault("timeline", []).append({
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "type": event_type,
            "summary": summary,
            "confidence": confidence,
        })
        self.state["timeline"] = self.state["timeline"][-500:]

    def dashboard(self):
        understanding = self.state.get("current_understanding") or self.understand_now()
        return {
            "title": "World Model",
            "status": "online",
            "understanding": understanding,
            "recent_timeline": self.state.get("timeline", [])[-10:],
            "memory": self.memory.snapshot(),
        }
''')

w('buster/perception/__init__.py', r'''
from .engine import PerceptionEngine
__all__ = ["PerceptionEngine"]
''')

w('buster/perception/engine.py', r'''
from buster.world_model import WorldModelEngine

class PerceptionEngine:
    def __init__(self, data_dir="data"):
        self.world = WorldModelEngine(data_dir=data_dir)

    def perceive_text(self, source, text, context=None, importance=0.5):
        obs = self.world.observe(source=source, summary=text, context=context or {}, importance=importance)
        understanding = self.world.understand_now()
        return {"observation": obs, "understanding": understanding}

    def perceive_camera_observation(self, description, objects=None, scene=None, confidence=0.75):
        context = {"objects": objects or [], "scene": scene or "unknown"}
        return self.world.observe("camera", description, context=context, importance=0.7, confidence=confidence)

    def perceive_desktop_observation(self, active_app, detail=""):
        summary = f"Desktop active app: {active_app}. {detail}".strip()
        return self.world.observe("desktop", summary, context={"active_app": active_app}, importance=0.6)
''')

w('buster/vision/world_model_bridge.py', r'''
try:
    from buster.world_model import WorldModelEngine
except Exception:
    WorldModelEngine = None

class VisionWorldModelBridge:
    def __init__(self, data_dir="data"):
        self.world = WorldModelEngine(data_dir=data_dir) if WorldModelEngine else None

    def record_scene(self, description, objects=None, scene="camera", confidence=0.75):
        if not self.world:
            return {"ok": False, "reason": "WorldModelEngine unavailable"}
        obs = self.world.observe(
            source="camera",
            summary=description,
            context={"objects": objects or [], "scene": scene},
            importance=0.7,
            confidence=confidence,
        )
        return {"ok": True, "observation": obs, "understanding": self.world.understand_now()}
''')

w('buster/brain/planner/world_model_planner_bridge.py', r'''
from buster.world_model import WorldModelEngine

class WorldModelPlannerBridge:
    def __init__(self, data_dir="data"):
        self.world = WorldModelEngine(data_dir=data_dir)

    def plan_from_world(self):
        understanding = self.world.understand_now()
        context = understanding.get("context", {})
        return {
            "mode": context.get("mode", "idle"),
            "signals": context.get("signals", []),
            "recommendation": understanding.get("recommendation"),
            "confidence": 0.85 if context.get("signals") else 0.65,
        }
''')

w('buster/workspace/world_model_dashboard.py', r'''
from buster.world_model import WorldModelEngine

class WorldModelDashboard:
    def __init__(self, data_dir="data"):
        self.engine = WorldModelEngine(data_dir=data_dir)

    def snapshot(self):
        return self.engine.dashboard()
''')

w('buster/ui/widgets/world_model_widget.py', r'''
class WorldModelWidgetModel:
    def __init__(self, snapshot=None):
        self.snapshot = snapshot or {}

    def as_lines(self):
        understanding = self.snapshot.get("understanding", {})
        context = understanding.get("context", {})
        lines = [
            "WORLD MODEL",
            f"Mode: {context.get('mode', 'unknown')}",
            f"Signals: {', '.join(context.get('signals', [])) or 'none'}",
            f"Recommendation: {understanding.get('recommendation', 'none')}",
        ]
        return lines
''')

w('buster/companion/__init__.py', r'''
from .engine import CompanionEngine
__all__ = ["CompanionEngine"]
''')

w('buster/companion/engine.py', r'''
from buster.world_model import WorldModelEngine

class CompanionEngine:
    def __init__(self, data_dir="data", name="Adam"):
        self.world = WorldModelEngine(data_dir=data_dir)
        self.name = name

    def morning_message(self):
        status = self.world.understand_now()
        mode = status.get("context", {}).get("mode", "idle")
        if mode == "android_development":
            return f"Good morning {self.name}. I can prepare Android monitoring when you are ready."
        if mode == "hardware_development":
            return f"Good morning {self.name}. I see hardware work may be active, so I can keep the device tools ready."
        return f"Good morning {self.name}. I'm online and watching for anything useful."

    def speak_from_world(self):
        status = self.world.understand_now()
        return status.get("recommendation", "I'm observing quietly.")
''')

# patch script main
print("=== Applying Buster v5.0 World Model AI OS Patch ===")
for path, text in FILES.items():
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    print(f"[WRITE] {path}")

# ensure data files
initials = {
    'data/world_model.json': {"entities": [], "observations": [], "relationships": [], "timeline": []},
    'data/perception_state.json': {"enabled": True, "sources": ["vision", "voice", "desktop", "hardware"]},
    'data/world_model_state.json': {"version": "5.0", "status": "online", "updated": datetime.now(timezone.utc).isoformat(timespec='seconds')},
    'data/companion_world_state.json': {"mode": "companion", "proactive": True},
}
for path, content in initials.items():
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(json.dumps(content, indent=2), encoding='utf-8')
        print(f"[CREATE] {path}")
    else:
        print(f"[SKIP] {path}")

print("\nSUCCESS: Buster v5.0 World Model AI OS installed.")
print("Next: python test_v5_0_world_model_ai_os.py")
