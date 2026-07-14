from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()

FILES = {}

def py(path, content):
    FILES[path] = content.strip() + "\n"

py('buster/perception/modes.py', r'''
from dataclasses import dataclass

PERCEPTION_MODES = {
    "off": {"camera": False, "microphone": False, "screen": False, "description": "No active sensing."},
    "wake_word": {"camera": False, "microphone": True, "screen": False, "description": "Listen only for wake activation."},
    "companion": {"camera": True, "microphone": True, "screen": True, "description": "Ambient local awareness for useful companion behaviour."},
    "development": {"camera": True, "microphone": True, "screen": True, "description": "Focus on IDEs, terminals, builds, devices, and project context."},
    "privacy": {"camera": False, "microphone": False, "screen": False, "description": "Temporarily pause observation while keeping Buster running."},
}

@dataclass
class PerceptionMode:
    name: str = "companion"

    def config(self):
        return PERCEPTION_MODES.get(self.name, PERCEPTION_MODES["companion"])

    def allows(self, sense: str) -> bool:
        return bool(self.config().get(sense, False))
''')

py('buster/perception/ears.py', r'''
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any

@dataclass
class AudioObservation:
    source: str = "microphone"
    sound_type: str = "unknown"
    confidence: float = 0.0
    text: str = ""
    speaker: str = "unknown"
    importance: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data["timestamp"]:
            data["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return data

class EarSystem:
    def observe(self, sound_type="speech", text="", speaker="unknown", confidence=0.5, importance=None):
        if importance is None:
            importance = self.score_importance(sound_type, text, confidence)
        return AudioObservation(sound_type=sound_type, text=text, speaker=speaker, confidence=confidence, importance=importance).to_dict()

    def score_importance(self, sound_type: str, text: str, confidence: float) -> float:
        score = confidence * 0.5
        lowered = (text or "").lower()
        if "buster" in lowered:
            score += 0.4
        if sound_type in {"alarm", "error", "device_connected"}:
            score += 0.3
        if sound_type == "speech":
            score += 0.1
        return max(0.0, min(1.0, score))
''')

py('buster/perception/eyes.py', r'''
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List

@dataclass
class VisualObservation:
    source: str = "camera"
    objects: List[str] = None
    scene: str = "unknown"
    confidence: float = 0.0
    importance: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["objects"] = data["objects"] or []
        if not data["timestamp"]:
            data["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return data

class EyeSystem:
    def observe(self, objects=None, scene="workspace", confidence=0.5, source="camera"):
        objects = objects or []
        importance = self.score_importance(objects, scene, confidence)
        return VisualObservation(source=source, objects=objects, scene=scene, confidence=confidence, importance=importance).to_dict()

    def score_importance(self, objects, scene, confidence):
        important = {"person", "phone", "esp32", "arduino", "laptop", "error", "screen"}
        score = confidence * 0.4
        score += min(0.4, len(set(o.lower() for o in objects) & important) * 0.15)
        if scene in {"development", "workspace", "hardware"}:
            score += 0.1
        return max(0.0, min(1.0, score))
''')

py('buster/perception/attention.py', r'''
class AttentionSystem:
    def choose_focus(self, observations):
        if not observations:
            return {"focus": "idle", "reason": "No observations", "importance": 0.0}
        ranked = sorted(observations, key=lambda o: float(o.get("importance", 0.0)), reverse=True)
        top = ranked[0]
        focus = top.get("sound_type") or top.get("scene") or top.get("source", "unknown")
        reason = "Wake word detected" if "buster" in str(top.get("text", "")).lower() else "Highest importance observation"
        return {"focus": focus, "reason": reason, "importance": float(top.get("importance", 0.0)), "observation": top}
''')

py('buster/perception/privacy.py', r'''
from dataclasses import dataclass

@dataclass
class PrivacyGate:
    mode: str = "companion"

    def allow_camera(self):
        return self.mode in {"companion", "development"}

    def allow_microphone(self):
        return self.mode in {"wake_word", "companion", "development"}

    def allow_screen(self):
        return self.mode in {"companion", "development"}

    def filter_observation(self, observation):
        source = observation.get("source", "")
        if source == "camera" and not self.allow_camera():
            return None
        if source == "microphone" and not self.allow_microphone():
            return None
        if source == "screen" and not self.allow_screen():
            return None
        return observation
''')

py('buster/perception/audio_learning.py', r'''
class AudioLearning:
    def __init__(self):
        self.phrases = {}

    def learn_phrase(self, phrase, meaning):
        key = phrase.strip().lower()
        self.phrases[key] = meaning
        return {"phrase": key, "meaning": meaning, "learned": True}

    def interpret(self, phrase):
        key = phrase.strip().lower()
        return self.phrases.get(key)
''')

py('buster/perception/perception_os.py', r'''
from pathlib import Path
import json
from datetime import datetime, timezone
from .ears import EarSystem
from .eyes import EyeSystem
from .attention import AttentionSystem
from .privacy import PrivacyGate

DATA = Path("data/perception_os_state.json")
OBS = Path("data/perception_observations.json")

class PerceptionOS:
    def __init__(self, mode="companion"):
        self.mode = mode
        self.ears = EarSystem()
        self.eyes = EyeSystem()
        self.attention = AttentionSystem()
        self.privacy = PrivacyGate(mode)

    def observe_audio(self, **kwargs):
        return self._record(self.privacy.filter_observation(self.ears.observe(**kwargs)))

    def observe_visual(self, **kwargs):
        return self._record(self.privacy.filter_observation(self.eyes.observe(**kwargs)))

    def _record(self, observation):
        if observation is None:
            return {"recorded": False, "reason": "Blocked by privacy mode", "mode": self.mode}
        OBS.parent.mkdir(parents=True, exist_ok=True)
        items = []
        if OBS.exists():
            try: items = json.loads(OBS.read_text(encoding="utf-8"))
            except Exception: items = []
        items.append(observation)
        OBS.write_text(json.dumps(items[-500:], indent=2), encoding="utf-8")
        focus = self.attention.choose_focus(items[-20:])
        state = {"mode": self.mode, "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "last_observation": observation, "attention": focus}
        DATA.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return {"recorded": True, "observation": observation, "attention": focus}

    def status(self):
        if DATA.exists():
            return json.loads(DATA.read_text(encoding="utf-8"))
        return {"mode": self.mode, "attention": {"focus": "idle"}}
''')

py('buster/world_model/perception_bridge.py', r'''
from datetime import datetime, timezone

class PerceptionWorldBridge:
    def observation_to_world_event(self, observation):
        kind = observation.get("sound_type") or observation.get("scene") or observation.get("source", "unknown")
        return {
            "type": "perception_observation",
            "kind": kind,
            "source": observation.get("source", "unknown"),
            "importance": observation.get("importance", 0.0),
            "confidence": observation.get("confidence", 0.0),
            "details": observation,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
''')

py('buster/workspace/perception_dashboard.py', r'''
from pathlib import Path
import json

class PerceptionDashboard:
    def __init__(self, state_path="data/perception_os_state.json"):
        self.state_path = Path(state_path)

    def snapshot(self):
        if not self.state_path.exists():
            return {"mode": "unknown", "focus": "idle", "status": "waiting"}
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        att = data.get("attention", {})
        return {
            "mode": data.get("mode", "unknown"),
            "focus": att.get("focus", "idle"),
            "importance": att.get("importance", 0.0),
            "reason": att.get("reason", ""),
            "updated": data.get("updated"),
        }
''')

py('buster/ui/widgets/perception_os_widget.py', r'''
class PerceptionOSWidgetModel:
    def build(self, snapshot):
        return {
            "title": "Perception OS",
            "mode": snapshot.get("mode", "unknown"),
            "focus": snapshot.get("focus", "idle"),
            "importance": snapshot.get("importance", 0.0),
            "reason": snapshot.get("reason", ""),
        }
''')

py('buster/brain/planner/perception_planner_bridge.py', r'''
class PerceptionPlannerBridge:
    def suggest(self, perception_snapshot):
        focus = perception_snapshot.get("focus", "idle")
        importance = float(perception_snapshot.get("importance", 0.0))
        if importance >= 0.75:
            return {"action": "notify_or_speak", "reason": f"Important perception event: {focus}"}
        if focus in {"speech", "alarm", "error"}:
            return {"action": "listen_and_update_context", "reason": f"Audio focus detected: {focus}"}
        return {"action": "observe_quietly", "reason": "No urgent perception event"}
''')

py('buster/perception/__init__.py', r'''
try:
    from .perception_os import PerceptionOS
    from .ears import EarSystem, AudioObservation
    from .eyes import EyeSystem, VisualObservation
    from .attention import AttentionSystem
    from .privacy import PrivacyGate
except Exception:
    pass
''')

# patch existing engine safely by appending imports only if no conflict? skip overwrite? We'll create data files.

def ensure_json(path, default):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(json.dumps(default, indent=2), encoding='utf-8')
        print(f"[CREATE] {path}")
    else:
        print(f"[SKIP] {path}")

print("=== Applying Buster v5.2 Perception OS + Ears Patch ===")
for rel, content in FILES.items():
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    print(f"[WRITE] {rel}")

ensure_json('data/perception_os_state.json', {"mode": "companion", "updated": datetime.now(timezone.utc).isoformat(timespec='seconds'), "attention": {"focus": "idle"}})
ensure_json('data/perception_observations.json', [])
ensure_json('data/audio_learning_memory.json', {"phrases": {}, "sounds": []})
ensure_json('data/attention_state.json', {"focus": "idle", "importance": 0.0})
ensure_json('data/perception_privacy_settings.json', {"mode": "companion", "camera": True, "microphone": True, "screen": True, "local_processing_preferred": True})

print("\nSUCCESS: Buster v5.2 Perception OS + Ears installed.")
print("Next: python test_v5_2_perception_os_ears.py")
