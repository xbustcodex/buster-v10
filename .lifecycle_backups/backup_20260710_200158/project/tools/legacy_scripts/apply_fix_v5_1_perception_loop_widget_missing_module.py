from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path.cwd()

def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    print(f"[WRITE] {path}")

def create_json(path, default):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(json.dumps(default, indent=2), encoding='utf-8')
        print(f"[CREATE] {path}")
    else:
        print(f"[SKIP] {path}")

print('=== Applying Buster v5.1 Perception Loop Widget Repair ===')

widget_code = r'''"""Perception loop widget model for Buster v5.1.

This is a lightweight, UI-safe model used by tests and Mission Control.
It does not depend on a GUI toolkit; real UI code can render this model.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any, Dict, List, Optional

DATA_DIR = Path("data")
STATE_FILE = DATA_DIR / "perception_loop_widget_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PerceptionLoopWidgetModel:
    """Presentation model for the real perception loop dashboard widget."""

    status: str = "idle"
    mode: str = "safe"
    last_update: str = field(default_factory=_now)
    observations: List[Dict[str, Any]] = field(default_factory=list)
    attention_focus: Optional[str] = None
    world_model_updates: int = 0
    companion_message: Optional[str] = None

    def update_status(self, status: str, mode: Optional[str] = None) -> Dict[str, Any]:
        self.status = status
        if mode is not None:
            self.mode = mode
        self.last_update = _now()
        self.save()
        return self.to_dict()

    def add_observation(self, source: str, summary: str, confidence: float = 0.0, **metadata: Any) -> Dict[str, Any]:
        item = {
            "time": _now(),
            "source": source,
            "summary": summary,
            "confidence": float(confidence),
            "metadata": metadata,
        }
        self.observations.append(item)
        self.observations = self.observations[-50:]
        self.last_update = item["time"]
        self.save()
        return item

    def set_attention(self, focus: Optional[str]) -> Dict[str, Any]:
        self.attention_focus = focus
        self.last_update = _now()
        self.save()
        return self.to_dict()

    def record_world_model_update(self, count: int = 1) -> Dict[str, Any]:
        self.world_model_updates += int(count)
        self.last_update = _now()
        self.save()
        return self.to_dict()

    def set_companion_message(self, message: Optional[str]) -> Dict[str, Any]:
        self.companion_message = message
        self.last_update = _now()
        self.save()
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def render(self) -> Dict[str, Any]:
        """Return UI-ready data without requiring PyQt/Tkinter imports."""
        return {
            "title": "Real Perception Loop",
            "status": self.status,
            "mode": self.mode,
            "last_update": self.last_update,
            "attention_focus": self.attention_focus or "none",
            "world_model_updates": self.world_model_updates,
            "latest_observations": self.observations[-10:],
            "companion_message": self.companion_message,
        }

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "PerceptionLoopWidgetModel":
        if not STATE_FILE.exists():
            return cls()
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return cls(**{k: data.get(k) for k in cls.__dataclass_fields__.keys() if k in data})
        except Exception:
            return cls(status="recovered")
'''

write('buster/ui/widgets/perception_loop_widget.py', widget_code)
create_json('data/perception_loop_widget_state.json', {
    'status': 'idle',
    'mode': 'safe',
    'last_update': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'observations': [],
    'attention_focus': None,
    'world_model_updates': 0,
    'companion_message': None,
})

print('\nSUCCESS: v5.1 missing PerceptionLoopWidgetModel repaired.')
print('Next: python -m pytest')
