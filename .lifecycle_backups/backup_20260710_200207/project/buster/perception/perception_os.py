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
