from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parent

FILES = {}

FILES['buster/workspace/mission_status.py'] = r'''
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class MissionStatus:
    name: str = "Buster AI OS"
    mode: str = "READY"
    confidence: float = 0.0
    risk: str = "unknown"
    active_agents: int = 0
    running_jobs: int = 0
    plugins_loaded: int = 0
    learning_entries: int = 0
    experience_entries: int = 0
    skills_tracked: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data.get("last_updated"):
            data["last_updated"] = datetime.utcnow().isoformat(timespec="seconds")
        return data


class MissionTimeline:
    def __init__(self, max_items: int = 100):
        self.max_items = max_items
        self.items: List[Dict[str, Any]] = []

    def add(self, event_type: str, message: str, source: str = "mission_control") -> Dict[str, Any]:
        item = {
            "time": datetime.utcnow().isoformat(timespec="seconds"),
            "event_type": event_type,
            "source": source,
            "message": message,
        }
        self.items.append(item)
        self.items = self.items[-self.max_items:]
        return item

    def latest(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(reversed(self.items[-limit:]))
'''

FILES['buster/workspace/mission_metrics.py'] = r'''
import json
from pathlib import Path
from typing import Any, Dict, List


class MissionMetrics:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def _load_json(self, name: str, default: Any) -> Any:
        path = self.data_dir / name
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _count_items(self, value: Any) -> int:
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for key in ("items", "records", "entries", "history", "events", "patterns", "strategies", "plugins", "skills"):
                if isinstance(value.get(key), list):
                    return len(value[key])
                if isinstance(value.get(key), dict):
                    return len(value[key])
            return len(value)
        return 0

    def collect(self) -> Dict[str, Any]:
        learning = self._load_json("learning_memory.json", [])
        experience = self._load_json("experience_memory.json", [])
        skills = self._load_json("skill_profiles.json", {})
        plugins = self._load_json("plugin_registry.json", {})
        autonomy = self._load_json("autonomy_state.json", {})
        intelligence = self._load_json("intelligence_state.json", {})
        events = self._load_json("event_history.json", [])

        return {
            "learning_entries": self._count_items(learning),
            "experience_entries": self._count_items(experience),
            "skills_tracked": self._count_items(skills),
            "plugins_loaded": self._count_items(plugins),
            "running_jobs": self._count_items(autonomy.get("running_jobs", [])) if isinstance(autonomy, dict) else 0,
            "active_agents": self._count_items(autonomy.get("active_agents", [])) if isinstance(autonomy, dict) else 0,
            "confidence": intelligence.get("confidence", 0.0) if isinstance(intelligence, dict) else 0.0,
            "risk": intelligence.get("risk", "unknown") if isinstance(intelligence, dict) else "unknown",
            "event_count": self._count_items(events),
        }
'''

FILES['buster/workspace/mission_control_dashboard.py'] = r'''
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .mission_metrics import MissionMetrics
from .mission_status import MissionStatus, MissionTimeline


class MissionControlDashboard:
    """Unified AI OS status view for Buster.

    Mission Control pulls together autonomy, intelligence, learning,
    experience, plugins, skills, events, agents and jobs into one snapshot.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = MissionMetrics(data_dir=str(self.data_dir))
        self.timeline = MissionTimeline()
        self.state_path = self.data_dir / "mission_control_dashboard.json"

    def snapshot(self) -> Dict[str, Any]:
        metrics = self.metrics.collect()
        status = MissionStatus(
            confidence=float(metrics.get("confidence") or 0.0),
            risk=str(metrics.get("risk") or "unknown"),
            active_agents=int(metrics.get("active_agents") or 0),
            running_jobs=int(metrics.get("running_jobs") or 0),
            plugins_loaded=int(metrics.get("plugins_loaded") or 0),
            learning_entries=int(metrics.get("learning_entries") or 0),
            experience_entries=int(metrics.get("experience_entries") or 0),
            skills_tracked=int(metrics.get("skills_tracked") or 0),
            last_updated=datetime.utcnow().isoformat(timespec="seconds"),
        ).to_dict()

        health = self.system_health(status)
        snapshot = {
            "version": "3.9",
            "title": "Buster Mission Control",
            "status": status,
            "metrics": metrics,
            "health": health,
            "timeline": self.timeline.latest(20),
        }
        self.save(snapshot)
        return snapshot

    def system_health(self, status: Dict[str, Any]) -> str:
        confidence = float(status.get("confidence") or 0.0)
        risk = str(status.get("risk") or "unknown").lower()
        if confidence >= 0.85 and risk in ("low", "safe", "unknown"):
            return "GOOD"
        if confidence >= 0.55 and risk not in ("critical", "high"):
            return "WATCH"
        return "CAUTION"

    def record_event(self, event_type: str, message: str, source: str = "mission_control") -> Dict[str, Any]:
        item = self.timeline.add(event_type, message, source)
        try:
            path = self.data_dir / "mission_timeline.json"
            existing = []
            if path.exists():
                existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
            existing.append(item)
            path.write_text(json.dumps(existing[-200:], indent=2), encoding="utf-8")
        except Exception:
            pass
        return item

    def save(self, snapshot: Dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    def render_text(self) -> str:
        snap = self.snapshot()
        s = snap["status"]
        return "\n".join([
            "=" * 54,
            "BUSTER MISSION CONTROL",
            "=" * 54,
            f"Mode: {s['mode']}  Health: {snap['health']}  Confidence: {s['confidence']}",
            f"Risk: {s['risk']}",
            f"Agents: {s['active_agents']}  Jobs: {s['running_jobs']}  Plugins: {s['plugins_loaded']}",
            f"Learning: {s['learning_entries']}  Experience: {s['experience_entries']}  Skills: {s['skills_tracked']}",
            f"Updated: {s['last_updated']}",
            "=" * 54,
        ])
'''

FILES['buster/ui/widgets/mission_control_widget.py'] = r'''
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None
    ttk = None

from buster.workspace.mission_control_dashboard import MissionControlDashboard


class MissionControlWidget:
    """Small Tkinter-compatible Mission Control panel.

    This stays optional so Buster can still run headless and in tests.
    """

    def __init__(self, parent=None, data_dir: str = "data"):
        self.parent = parent
        self.dashboard = MissionControlDashboard(data_dir=data_dir)
        self.frame = None
        self.text = None
        if tk is not None and parent is not None:
            self.frame = ttk.Frame(parent) if ttk else tk.Frame(parent)
            self.text = tk.Text(self.frame, height=9, width=62)
            self.text.pack(fill="both", expand=True)
            self.refresh()

    def refresh(self):
        content = self.dashboard.render_text()
        if self.text is not None:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
        return content

    def pack(self, *args, **kwargs):
        if self.frame is not None:
            self.frame.pack(*args, **kwargs)
'''

FILES['buster/brain/planner/mission_planner.py'] = r'''
from typing import Any, Dict, List

from buster.workspace.mission_control_dashboard import MissionControlDashboard


class MissionPlanner:
    """Planner helper that checks Mission Control before choosing actions."""

    def __init__(self, data_dir: str = "data"):
        self.dashboard = MissionControlDashboard(data_dir=data_dir)

    def recommend(self, request: str = "") -> Dict[str, Any]:
        snap = self.dashboard.snapshot()
        health = snap.get("health", "WATCH")
        status = snap.get("status", {})
        confidence = float(status.get("confidence") or 0.0)
        risk = str(status.get("risk") or "unknown")

        actions: List[str] = []
        if health == "GOOD":
            actions.append("Proceed with autonomous execution")
        elif health == "WATCH":
            actions.append("Proceed with verification checkpoints")
        else:
            actions.append("Ask user before executing risky changes")

        if status.get("plugins_loaded", 0) == 0:
            actions.append("Refresh plugin registry")
        if status.get("learning_entries", 0) == 0:
            actions.append("Record first learning outcome")
        if status.get("experience_entries", 0) == 0:
            actions.append("Record first project experience")

        return {
            "request": request,
            "health": health,
            "confidence": confidence,
            "risk": risk,
            "recommended_actions": actions,
        }
'''

FILES['buster/workspace/__init__.py'] = r'''
# Buster workspace package

try:
    from .mission_control_dashboard import MissionControlDashboard
except Exception:  # keep imports safe during partial installs
    MissionControlDashboard = None
'''

FILES['BUSTER_AI_OS_ARCHITECTURE.md'] = r'''# Buster AI OS Architecture

Buster is evolving from a desktop companion into a Jarvis-level AI operating environment.

## Core Layers

- Brain: conversation, providers, planner, intent handling.
- Intelligence: confidence, risk analysis, reasoning, scoring and strategy selection.
- Memory: long-term facts and knowledge.
- Learning: what worked, what failed and reusable patterns.
- Experience: engineering outcomes, project experience, skills and user overrides.
- Autonomy: next actions, job awareness and self-directed recommendations.
- Event Bus: shared communication channel for subsystems.
- Plugin OS: installable capabilities without growing the core into one huge file.
- Mission Control: unified dashboard showing system health, confidence, agents, jobs, plugins, learning, experience and skills.

## Design Rule

Buster should become smarter over time without becoming one massive file.

Every new capability should be one of:

1. Core subsystem
2. Agent
3. Plugin
4. Dashboard/widget
5. Data store

## v3.9 Goal

Mission Control becomes the main AI OS view.
It does not replace the existing dashboard yet; it provides a clean backend and optional widget that can be integrated into the existing UI.
'''


def write_file(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"[WRITE] {rel}")


def create_json(rel: str, default):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        print(f"[CREATE] {rel}")
    else:
        print(f"[OK] {rel}")


def main():
    print("=== Applying Buster v3.9 Mission Control Dashboard Patch ===")
    for rel, content in FILES.items():
        write_file(rel, content)

    create_json("data/mission_control_dashboard.json", {
        "version": "3.9",
        "title": "Buster Mission Control",
        "status": {},
        "metrics": {},
        "health": "READY",
        "timeline": [],
    })
    create_json("data/mission_timeline.json", [])
    create_json("data/ai_os_architecture_state.json", {
        "version": "3.9",
        "architecture": "Buster AI OS",
        "updated": datetime.utcnow().isoformat(timespec="seconds"),
        "subsystems": [
            "brain", "memory", "learning", "experience", "intelligence",
            "autonomy", "plugins", "repository", "vision", "voice", "mission_control"
        ]
    })

    print("\nSUCCESS: Buster v3.9 Mission Control Dashboard installed.")
    print("Next: python test_v3_9_mission_control_dashboard.py")


if __name__ == "__main__":
    main()
