from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()

FILES = {}

FILES['buster/mind/__init__.py'] = r'''"""Buster Mind cognitive architecture.

The Mind layer connects perception, attention, working memory, goals,
reasoning, planning, agents, learning, and companion behaviour.
"""

from .attention_system import AttentionSystem
from .working_memory import WorkingMemory
from .goal_manager import GoalManager
from .reflection import ReflectionCycle
from .curiosity import CuriosityEngine
from .engine import MindEngine

__all__ = [
    "AttentionSystem",
    "WorkingMemory",
    "GoalManager",
    "ReflectionCycle",
    "CuriosityEngine",
    "MindEngine",
]
'''

FILES['buster/mind/storage.py'] = r'''from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from datetime import datetime, timezone

DATA_DIR = Path("data")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: str | Path, default: Any) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_record(path: str | Path, record: Dict[str, Any], limit: int = 500) -> Dict[str, Any]:
    records = load_json(path, [])
    if not isinstance(records, list):
        records = []
    records.append(record)
    if len(records) > limit:
        records = records[-limit:]
    save_json(path, records)
    return record
'''

FILES['buster/mind/attention_system.py'] = r'''from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from .storage import load_json, save_json, append_record, now_iso

ATTENTION_STATE = "data/attention_focus.json"
ATTENTION_EVENTS = "data/attention_events.json"


@dataclass
class AttentionEvent:
    source: str
    kind: str
    title: str
    details: str = ""
    importance: float = 0.5
    urgency: float = 0.5
    confidence: float = 0.5
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data["timestamp"]:
            data["timestamp"] = now_iso()
        data["priority"] = round((data["importance"] * 0.45) + (data["urgency"] * 0.35) + (data["confidence"] * 0.20), 3)
        return data


class AttentionSystem:
    """Filters perception into what Buster should focus on.

    This is not a speech recognizer or camera engine. It is the cognitive gate
    that decides which observations deserve working-memory space.
    """

    def __init__(self, state_path: str = ATTENTION_STATE, events_path: str = ATTENTION_EVENTS):
        self.state_path = state_path
        self.events_path = events_path
        self.threshold = 0.62

    def score(self, event: Dict[str, Any]) -> float:
        importance = float(event.get("importance", 0.5))
        urgency = float(event.get("urgency", 0.5))
        confidence = float(event.get("confidence", 0.5))
        # Wake words, failed builds, device changes, and mission completions are boosted.
        kind = str(event.get("kind", "")).lower()
        boost = 0.0
        if kind in {"wake_word", "build_failed", "test_failed", "device_connected", "mission_complete", "user_returned"}:
            boost = 0.18
        return round(min(1.0, (importance * 0.45) + (urgency * 0.35) + (confidence * 0.20) + boost), 3)

    def observe(self, source: str, kind: str, title: str, details: str = "", importance: float = 0.5, urgency: float = 0.5, confidence: float = 0.5) -> Dict[str, Any]:
        event = AttentionEvent(source, kind, title, details, importance, urgency, confidence).to_dict()
        event["priority"] = self.score(event)
        event["focused"] = event["priority"] >= self.threshold
        append_record(self.events_path, event)
        if event["focused"]:
            state = self.get_state()
            state["current_focus"] = event
            state["updated"] = now_iso()
            state.setdefault("focus_history", []).append(event)
            state["focus_history"] = state["focus_history"][-50:]
            save_json(self.state_path, state)
        return event

    def get_state(self) -> Dict[str, Any]:
        return load_json(self.state_path, {"current_focus": None, "focus_history": [], "updated": now_iso()})

    def recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        events = load_json(self.events_path, [])
        if not isinstance(events, list):
            return []
        return events[-limit:]
'''

FILES['buster/mind/working_memory.py'] = r'''from __future__ import annotations

from typing import Any, Dict, List

from .storage import load_json, save_json, now_iso

WORKING_MEMORY = "data/working_memory.json"


class WorkingMemory:
    """Small active context window: what Buster is thinking about now."""

    def __init__(self, path: str = WORKING_MEMORY, capacity: int = 12):
        self.path = path
        self.capacity = capacity

    def get_state(self) -> Dict[str, Any]:
        return load_json(self.path, {"items": [], "current_mission": None, "updated": now_iso()})

    def remember(self, item_type: str, title: str, data: Dict[str, Any] | None = None, priority: float = 0.5) -> Dict[str, Any]:
        state = self.get_state()
        item = {
            "type": item_type,
            "title": title,
            "data": data or {},
            "priority": round(float(priority), 3),
            "timestamp": now_iso(),
        }
        items = state.get("items", [])
        items.append(item)
        items = sorted(items, key=lambda x: (x.get("priority", 0), x.get("timestamp", "")), reverse=True)[: self.capacity]
        state["items"] = items
        state["updated"] = now_iso()
        save_json(self.path, state)
        return item

    def set_current_mission(self, mission: Dict[str, Any]) -> None:
        state = self.get_state()
        state["current_mission"] = mission
        state["updated"] = now_iso()
        save_json(self.path, state)

    def clear(self) -> None:
        save_json(self.path, {"items": [], "current_mission": None, "updated": now_iso()})

    def summary(self) -> Dict[str, Any]:
        state = self.get_state()
        return {
            "active_items": len(state.get("items", [])),
            "current_mission": state.get("current_mission"),
            "top_items": state.get("items", [])[:5],
            "updated": state.get("updated"),
        }
'''

FILES['buster/mind/goal_manager.py'] = r'''from __future__ import annotations

from typing import Any, Dict, List

from .storage import load_json, save_json, now_iso

GOALS = "data/goals.json"


class GoalManager:
    """Tracks objectives Buster can pursue over time."""

    def __init__(self, path: str = GOALS):
        self.path = path

    def _state(self) -> Dict[str, Any]:
        return load_json(self.path, {"goals": [], "updated": now_iso()})

    def create_goal(self, title: str, description: str = "", priority: float = 0.5, source: str = "user") -> Dict[str, Any]:
        state = self._state()
        goal = {
            "id": f"goal_{len(state.get('goals', [])) + 1}_{int(__import__('time').time())}",
            "title": title,
            "description": description,
            "priority": round(float(priority), 3),
            "source": source,
            "status": "active",
            "progress": 0.0,
            "created": now_iso(),
            "updated": now_iso(),
            "subgoals": [],
        }
        state.setdefault("goals", []).append(goal)
        state["updated"] = now_iso()
        save_json(self.path, state)
        return goal

    def add_subgoal(self, goal_id: str, title: str) -> Dict[str, Any] | None:
        state = self._state()
        for goal in state.get("goals", []):
            if goal.get("id") == goal_id:
                sub = {"title": title, "status": "pending", "created": now_iso()}
                goal.setdefault("subgoals", []).append(sub)
                goal["updated"] = now_iso()
                save_json(self.path, state)
                return sub
        return None

    def update_goal(self, goal_id: str, status: str | None = None, progress: float | None = None) -> Dict[str, Any] | None:
        state = self._state()
        for goal in state.get("goals", []):
            if goal.get("id") == goal_id:
                if status is not None:
                    goal["status"] = status
                if progress is not None:
                    goal["progress"] = max(0.0, min(1.0, float(progress)))
                goal["updated"] = now_iso()
                save_json(self.path, state)
                return goal
        return None

    def active_goals(self) -> List[Dict[str, Any]]:
        goals = self._state().get("goals", [])
        return sorted([g for g in goals if g.get("status") == "active"], key=lambda g: g.get("priority", 0), reverse=True)
'''

FILES['buster/mind/curiosity.py'] = r'''from __future__ import annotations

from typing import Any, Dict, List

from .storage import load_json, append_record, now_iso

CURIOSITY_LOG = "data/curiosity_log.json"


class CuriosityEngine:
    """Finds useful improvement opportunities from repeated patterns."""

    def __init__(self, log_path: str = CURIOSITY_LOG):
        self.log_path = log_path

    def inspect_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        for pattern in patterns:
            count = int(pattern.get("count", pattern.get("uses", 0)) or 0)
            name = pattern.get("name") or pattern.get("title") or "Repeated pattern"
            domain = pattern.get("domain", "general")
            if count >= 3:
                suggestions.append({
                    "type": "automation_opportunity",
                    "title": f"Create reusable solution for {name}",
                    "reason": f"Seen {count} times in {domain} work.",
                    "confidence": min(0.99, 0.55 + (count * 0.08)),
                    "timestamp": now_iso(),
                })
        for item in suggestions:
            append_record(self.log_path, item)
        return suggestions

    def suggest_from_memory(self) -> List[Dict[str, Any]]:
        learning = load_json("data/learning_memory.json", [])
        if isinstance(learning, dict):
            candidates = learning.get("patterns", []) or learning.get("records", []) or []
        elif isinstance(learning, list):
            candidates = learning
        else:
            candidates = []
        return self.inspect_patterns(candidates)
'''

FILES['buster/mind/reflection.py'] = r'''from __future__ import annotations

from typing import Any, Dict

from .storage import load_json, append_record, now_iso

REFLECTIONS = "data/reflection_journal.json"


class ReflectionCycle:
    """Idle-time maintenance: summarize, compress, and learn from the day."""

    def __init__(self, path: str = REFLECTIONS):
        self.path = path

    def run_daily_reflection(self) -> Dict[str, Any]:
        timeline = load_json("data/mission_timeline_live.json", [])
        experience = load_json("data/experience_memory.json", [])
        skills = load_json("data/skill_profiles.json", {})
        events = timeline[-20:] if isinstance(timeline, list) else []
        reflection = {
            "timestamp": now_iso(),
            "title": "Daily reflection",
            "summary": f"Reviewed {len(events)} recent mission events.",
            "recent_events": events[-8:],
            "skill_snapshot": skills if isinstance(skills, dict) else {},
            "experience_records": len(experience) if isinstance(experience, list) else len(experience.keys()) if isinstance(experience, dict) else 0,
            "recommendations": [],
        }
        if len(events) >= 5:
            reflection["recommendations"].append("Promote repeated successful mission steps into reusable strategies.")
        if reflection["experience_records"] >= 3:
            reflection["recommendations"].append("Review experience records for reusable project templates.")
        append_record(self.path, reflection)
        return reflection
'''

FILES['buster/mind/engine.py'] = r'''from __future__ import annotations

from typing import Any, Dict

from .attention_system import AttentionSystem
from .working_memory import WorkingMemory
from .goal_manager import GoalManager
from .curiosity import CuriosityEngine
from .reflection import ReflectionCycle
from .storage import load_json, save_json, now_iso

MIND_STATE = "data/mind_state.json"


class MindEngine:
    """Buster cognitive control layer.

    Perception feeds attention. Important events enter working memory.
    Goals and curiosity guide planning. Reflection improves long-term behaviour.
    """

    def __init__(self):
        self.attention = AttentionSystem()
        self.working_memory = WorkingMemory()
        self.goals = GoalManager()
        self.curiosity = CuriosityEngine()
        self.reflection = ReflectionCycle()

    def perceive(self, source: str, kind: str, title: str, details: str = "", importance: float = 0.5, urgency: float = 0.5, confidence: float = 0.5) -> Dict[str, Any]:
        event = self.attention.observe(source, kind, title, details, importance, urgency, confidence)
        if event.get("focused"):
            self.working_memory.remember("attention_event", title, event, priority=event.get("priority", 0.5))
        self._update_state(last_event=event)
        return event

    def create_goal_from_focus(self) -> Dict[str, Any] | None:
        focus = self.attention.get_state().get("current_focus")
        if not focus:
            return None
        if focus.get("priority", 0) < 0.75:
            return None
        return self.goals.create_goal(
            title=f"Respond to {focus.get('title')}",
            description=focus.get("details", ""),
            priority=focus.get("priority", 0.5),
            source=focus.get("source", "attention"),
        )

    def think(self) -> Dict[str, Any]:
        state = {
            "timestamp": now_iso(),
            "attention": self.attention.get_state(),
            "working_memory": self.working_memory.summary(),
            "active_goals": self.goals.active_goals()[:5],
            "curiosity_suggestions": self.curiosity.suggest_from_memory()[:5],
        }
        save_json(MIND_STATE, state)
        return state

    def reflect(self) -> Dict[str, Any]:
        result = self.reflection.run_daily_reflection()
        self._update_state(last_reflection=result)
        return result

    def _update_state(self, **updates: Any) -> None:
        state = load_json(MIND_STATE, {"created": now_iso()})
        state.update(updates)
        state["updated"] = now_iso()
        save_json(MIND_STATE, state)
'''

FILES['buster/perception/mind_bridge.py'] = r'''from __future__ import annotations

from typing import Any, Dict

try:
    from buster.mind import MindEngine
except Exception:  # pragma: no cover
    MindEngine = None  # type: ignore


class PerceptionMindBridge:
    """Routes eyes/ears/screen/device observations into the Mind layer."""

    def __init__(self, mind: Any | None = None):
        self.mind = mind or (MindEngine() if MindEngine else None)

    def submit_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        if self.mind is None:
            return {"accepted": False, "reason": "MindEngine unavailable", "observation": observation}
        return self.mind.perceive(
            source=observation.get("source", "perception"),
            kind=observation.get("kind", "observation"),
            title=observation.get("title", "Observation"),
            details=observation.get("details", ""),
            importance=float(observation.get("importance", 0.5)),
            urgency=float(observation.get("urgency", 0.5)),
            confidence=float(observation.get("confidence", 0.5)),
        )
'''

FILES['buster/world_model/mind_bridge.py'] = r'''from __future__ import annotations

from typing import Any, Dict

from buster.mind.storage import load_json, save_json, now_iso

WORLD_MIND_STATE = "data/world_model_mind_state.json"


class WorldModelMindBridge:
    """Summarizes the world model into cognitive context for the Mind layer."""

    def summarize_world(self) -> Dict[str, Any]:
        world = load_json("data/world_model.json", {})
        summary = {
            "timestamp": now_iso(),
            "entities": len(world.get("entities", [])) if isinstance(world, dict) else 0,
            "relationships": len(world.get("relationships", [])) if isinstance(world, dict) else 0,
            "observations": len(world.get("observations", [])) if isinstance(world, dict) else 0,
            "active_context": world.get("active_context", {}) if isinstance(world, dict) else {},
        }
        save_json(WORLD_MIND_STATE, summary)
        return summary
'''

FILES['buster/brain/planner/mind_planner_bridge.py'] = r'''from __future__ import annotations

from typing import Any, Dict

from buster.mind import MindEngine


class MindPlannerBridge:
    """Gives planners access to attention, working memory, goals, and curiosity."""

    def __init__(self, mind: MindEngine | None = None):
        self.mind = mind or MindEngine()

    def prepare_planning_context(self) -> Dict[str, Any]:
        thought = self.mind.think()
        return {
            "focus": thought.get("attention", {}).get("current_focus"),
            "working_memory": thought.get("working_memory"),
            "active_goals": thought.get("active_goals", []),
            "curiosity_suggestions": thought.get("curiosity_suggestions", []),
        }

    def should_act_now(self) -> bool:
        ctx = self.prepare_planning_context()
        focus = ctx.get("focus") or {}
        return float(focus.get("priority", 0)) >= 0.72
'''

FILES['buster/workspace/mind_dashboard.py'] = r'''from __future__ import annotations

from typing import Any, Dict

from buster.mind import MindEngine


class MindDashboard:
    """Dashboard model for Mission Control's cognitive view."""

    def __init__(self, mind: MindEngine | None = None):
        self.mind = mind or MindEngine()

    def snapshot(self) -> Dict[str, Any]:
        state = self.mind.think()
        return {
            "title": "Buster Mind",
            "current_focus": state.get("attention", {}).get("current_focus"),
            "working_memory": state.get("working_memory"),
            "active_goals": state.get("active_goals", []),
            "curiosity": state.get("curiosity_suggestions", []),
            "status": "thinking" if state.get("attention", {}).get("current_focus") else "relaxed",
        }
'''

FILES['buster/ui/widgets/mind_widget.py'] = r'''from __future__ import annotations

from typing import Any, Dict

try:
    from buster.workspace.mind_dashboard import MindDashboard
except Exception:  # pragma: no cover
    MindDashboard = None  # type: ignore


class MindWidgetModel:
    """Pure data model for a future UI widget; no GUI dependency required."""

    def __init__(self):
        self.dashboard = MindDashboard() if MindDashboard else None

    def render_model(self) -> Dict[str, Any]:
        if self.dashboard is None:
            return {"title": "Buster Mind", "status": "unavailable"}
        return self.dashboard.snapshot()
'''

FILES['buster/companion/mind_companion_bridge.py'] = r'''from __future__ import annotations

from typing import Any, Dict, List

from buster.mind import MindEngine


class MindCompanionBridge:
    """Turns cognitive state into meaningful companion messages."""

    def __init__(self, mind: MindEngine | None = None):
        self.mind = mind or MindEngine()

    def suggestions(self) -> List[str]:
        state = self.mind.think()
        messages: List[str] = []
        focus = state.get("attention", {}).get("current_focus")
        if focus and focus.get("priority", 0) >= 0.75:
            messages.append(f"I noticed {focus.get('title')}. Priority is {focus.get('priority')}. I can help with that.")
        for item in state.get("curiosity_suggestions", [])[:2]:
            messages.append(item.get("title", "I found a useful improvement opportunity."))
        return messages
'''

FILES['BUSTER_MIND_ARCHITECTURE.md'] = r'''# Buster Mind Architecture

Buster is moving from a feature-based assistant to a cognitive AI operating system.

## Core Loop

Perceive → Attend → Remember → Model → Reason → Goal → Plan → Act → Learn → Reflect

## Cognitive Layers

1. **Perception**: eyes, ears, screen, devices, projects, environment.
2. **Attention**: filters what deserves focus.
3. **Working Memory**: current mission, current conversation, current screen/context.
4. **World Model**: what Buster believes is happening.
5. **Reasoning**: meaning, confidence, risk, strategy.
6. **Goal Manager**: persistent objectives and sub-goals.
7. **Agent Teams**: builders, testers, fixers, reviewers, verifiers, plugins.
8. **Learning and Experience**: patterns, skills, outcomes, reusable strategies.
9. **Companion**: voice, face, presence, natural proactive communication.
10. **Reflection**: idle-time consolidation and improvement.

## Design Rule

Every new subsystem must answer:

> Does this help Buster understand its world better?

If yes, it belongs in the AI OS. If no, it should remain a plugin or be left out.
'''

FILES['test_v5_3_buster_mind.py'] = r'''from pathlib import Path


def test_imports():
    from buster.mind import MindEngine, AttentionSystem, WorkingMemory, GoalManager, CuriosityEngine, ReflectionCycle
    assert MindEngine
    assert AttentionSystem
    assert WorkingMemory
    assert GoalManager
    assert CuriosityEngine
    assert ReflectionCycle


def test_attention_working_memory_goal_flow():
    from buster.mind import MindEngine
    mind = MindEngine()
    event = mind.perceive(
        source="ears",
        kind="wake_word",
        title="Adam said Buster",
        details="Wake word detected by microphone",
        importance=0.9,
        urgency=0.85,
        confidence=0.95,
    )
    assert event["focused"] is True
    assert event["priority"] >= 0.72
    goal = mind.create_goal_from_focus()
    assert goal is not None
    assert goal["status"] == "active"
    thought = mind.think()
    assert thought["working_memory"]["active_items"] >= 1
    assert len(thought["active_goals"]) >= 1


def test_bridges_and_dashboard():
    from buster.perception.mind_bridge import PerceptionMindBridge
    from buster.brain.planner.mind_planner_bridge import MindPlannerBridge
    from buster.workspace.mind_dashboard import MindDashboard
    bridge = PerceptionMindBridge()
    result = bridge.submit_observation({
        "source": "camera",
        "kind": "user_returned",
        "title": "User returned to desk",
        "importance": 0.8,
        "urgency": 0.6,
        "confidence": 0.8,
    })
    assert "priority" in result
    planner = MindPlannerBridge()
    ctx = planner.prepare_planning_context()
    assert "working_memory" in ctx
    dash = MindDashboard().snapshot()
    assert dash["title"] == "Buster Mind"


def test_reflection_and_files_exist():
    from buster.mind import MindEngine
    reflection = MindEngine().reflect()
    assert reflection["title"] == "Daily reflection"
    for p in [
        "data/mind_state.json",
        "data/attention_focus.json",
        "data/attention_events.json",
        "data/working_memory.json",
        "data/goals.json",
        "data/reflection_journal.json",
    ]:
        assert Path(p).exists()


if __name__ == "__main__":
    test_imports()
    test_attention_working_memory_goal_flow()
    test_bridges_and_dashboard()
    test_reflection_and_files_exist()
    print("SUCCESS: v5.3 Buster Mind tests passed")
'''

INITIAL_JSON = {
    'data/mind_state.json': {"status": "ready", "created": None},
    'data/attention_focus.json': {"current_focus": None, "focus_history": [], "updated": None},
    'data/attention_events.json': [],
    'data/working_memory.json': {"items": [], "current_mission": None, "updated": None},
    'data/goals.json': {"goals": [], "updated": None},
    'data/curiosity_log.json': [],
    'data/reflection_journal.json': [],
    'data/world_model_mind_state.json': {},
}


def write_file(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f"[WRITE] {rel}")


def create_json(rel, data):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f"[SKIP] {rel}")
        return
    def stamp(obj):
        if isinstance(obj, dict):
            return {k: (datetime.now(timezone.utc).isoformat(timespec='seconds') if v is None else stamp(v)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [stamp(v) for v in obj]
        return obj
    path.write_text(json.dumps(stamp(data), indent=2), encoding='utf-8')
    print(f"[CREATE] {rel}")


def main():
    print("=== Applying Buster v5.3 Cognitive Mind Patch ===")
    for rel, content in FILES.items():
        write_file(rel, content)
    for rel, data in INITIAL_JSON.items():
        create_json(rel, data)
    print("\nSUCCESS: Buster v5.3 Cognitive Mind installed.")
    print("Next: python test_v5_3_buster_mind.py")


if __name__ == '__main__':
    main()
