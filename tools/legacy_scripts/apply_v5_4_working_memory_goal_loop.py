from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path.cwd()

def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + '\n', encoding='utf-8')
    print(f"[WRITE] {path}")

def create_json(path, value):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        print(f"[SKIP] {path}")
        return
    p.write_text(json.dumps(value, indent=2), encoding='utf-8')
    print(f"[CREATE] {path}")

print("=== Applying Buster v5.4 Working Memory + Goal Loop Patch ===")

write("buster/mind/mission_context.py", r'''
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

@dataclass
class MissionContext:
    mission_id: str
    title: str
    status: str = "active"
    priority: int = 5
    confidence: float = 0.75
    risk: str = "medium"
    active_goal_ids: List[str] = None
    current_focus: str = ""
    notes: List[str] = None
    updated_at: str = ""

    def __post_init__(self):
        if self.active_goal_ids is None:
            self.active_goal_ids = []
        if self.notes is None:
            self.notes = []
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MissionContextManager:
    def __init__(self):
        self.current: Optional[MissionContext] = None

    def start(self, title: str, mission_id: Optional[str] = None, priority: int = 5) -> MissionContext:
        mission_id = mission_id or "mission_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.current = MissionContext(mission_id=mission_id, title=title, priority=priority)
        return self.current

    def attach_goal(self, goal_id: str) -> None:
        if not self.current:
            self.start("General mission")
        if goal_id not in self.current.active_goal_ids:
            self.current.active_goal_ids.append(goal_id)
            self.touch()

    def set_focus(self, focus: str) -> None:
        if not self.current:
            self.start("General mission")
        self.current.current_focus = focus
        self.touch()

    def note(self, message: str) -> None:
        if not self.current:
            self.start("General mission")
        self.current.notes.append(message)
        self.touch()

    def touch(self) -> None:
        if self.current:
            self.current.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def snapshot(self) -> Dict[str, Any]:
        return self.current.to_dict() if self.current else {}
''')

write("buster/mind/goal_loop.py", r'''
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

@dataclass
class Goal:
    goal_id: str
    title: str
    source: str = "user"
    priority: int = 5
    status: str = "open"
    confidence: float = 0.75
    risk: str = "medium"
    evidence: List[str] = None
    next_action: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.evidence is None:
            self.evidence = []
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class GoalLoop:
    def __init__(self):
        self.goals: Dict[str, Goal] = {}

    def create_goal(self, title: str, source: str = "user", priority: int = 5, evidence: Optional[List[str]] = None) -> Goal:
        goal_id = "goal_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        goal = Goal(goal_id=goal_id, title=title, source=source, priority=priority, evidence=evidence or [])
        goal.next_action = self.recommend_next_action(goal)
        self.goals[goal_id] = goal
        return goal

    def observe(self, observation: Dict[str, Any]) -> Optional[Goal]:
        text = str(observation.get("text") or observation.get("label") or observation.get("event") or "").lower()
        source = str(observation.get("source", "observation"))
        if any(k in text for k in ["error", "failed", "crash", "exception"]):
            return self.create_goal("Investigate and fix detected problem", source=source, priority=9, evidence=[text])
        if any(k in text for k in ["android studio", "esp32", "arduino", "pixel connected", "repository changed"]):
            return self.create_goal("Prepare workspace for detected development context", source=source, priority=7, evidence=[text])
        if any(k in text for k in ["idle", "away", "inactive"]):
            return self.create_goal("Monitor workspace quietly until user returns", source=source, priority=3, evidence=[text])
        return None

    def recommend_next_action(self, goal: Goal) -> str:
        title = goal.title.lower()
        if "fix" in title or "problem" in title:
            return "Ask Fixer Agent to inspect logs and propose repair."
        if "workspace" in title:
            return "Load relevant plugins, index project, and prepare Mission Control."
        if "quietly" in title:
            return "Reduce speech frequency and continue ambient monitoring."
        return "Create mission plan and assign the best available agent."

    def active_goals(self) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self.goals.values() if g.status in ("open", "active")]

    def complete_goal(self, goal_id: str, result: str = "completed") -> bool:
        goal = self.goals.get(goal_id)
        if not goal:
            return False
        goal.status = result
        goal.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return True
''')

write("buster/mind/context_priority.py", r'''
from typing import Any, Dict, List

class ContextPrioritizer:
    def score(self, item: Dict[str, Any]) -> float:
        priority = float(item.get("priority", 5))
        confidence = float(item.get("confidence", 0.75))
        risk = str(item.get("risk", "medium")).lower()
        risk_bonus = {"low": 0.0, "medium": 1.0, "high": 2.0, "critical": 3.0}.get(risk, 1.0)
        age_penalty = float(item.get("age_penalty", 0))
        return max(0.0, priority + risk_bonus + confidence - age_penalty)

    def sort(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(items, key=self.score, reverse=True)

    def top(self, items: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        return self.sort(items)[:limit]
''')

write("buster/mind/companion_context.py", r'''
from typing import Any, Dict, List

class CompanionContextBuilder:
    def build(self, mission: Dict[str, Any], goals: List[Dict[str, Any]], focus: List[Dict[str, Any]]) -> Dict[str, Any]:
        active_goal = goals[0] if goals else None
        return {
            "mode": "companion",
            "mission": mission,
            "active_goal": active_goal,
            "focus": focus,
            "suggested_speech": self.suggest_speech(mission, active_goal, focus),
        }

    def suggest_speech(self, mission: Dict[str, Any], goal: Dict[str, Any] | None, focus: List[Dict[str, Any]]) -> str:
        if goal:
            return f"I noticed something useful: {goal.get('title')}. {goal.get('next_action', '')}"
        if mission:
            return f"I'm tracking the mission: {mission.get('title', 'current work')}."
        if focus:
            return "I'm watching the important workspace signals and will speak only if something useful happens."
        return "I'm here and monitoring quietly."
''')

write("buster/mind/work_loop.py", r'''
from typing import Any, Dict, List
from .mission_context import MissionContextManager
from .goal_loop import GoalLoop
from .context_priority import ContextPrioritizer
from .companion_context import CompanionContextBuilder

class WorkingMemoryGoalLoop:
    def __init__(self):
        self.missions = MissionContextManager()
        self.goals = GoalLoop()
        self.prioritizer = ContextPrioritizer()
        self.companion = CompanionContextBuilder()
        self.focus_items: List[Dict[str, Any]] = []

    def start_mission(self, title: str, priority: int = 5) -> Dict[str, Any]:
        return self.missions.start(title, priority=priority).to_dict()

    def ingest_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        goal = self.goals.observe(observation)
        focus = dict(observation)
        focus.setdefault("priority", goal.priority if goal else observation.get("priority", 4))
        self.focus_items.append(focus)
        if goal:
            self.missions.attach_goal(goal.goal_id)
            self.missions.set_focus(goal.title)
        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        focus = self.prioritizer.top(self.focus_items, limit=8)
        goals = self.prioritizer.top(self.goals.active_goals(), limit=8)
        mission = self.missions.snapshot()
        return {
            "mission": mission,
            "goals": goals,
            "focus": focus,
            "companion_context": self.companion.build(mission, goals, focus),
        }
''')

write("buster/workspace/working_memory_goal_dashboard.py", r'''
from typing import Any, Dict

class WorkingMemoryGoalDashboard:
    def render_model(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        mission = snapshot.get("mission", {})
        goals = snapshot.get("goals", [])
        focus = snapshot.get("focus", [])
        companion = snapshot.get("companion_context", {})
        return {
            "title": "Working Memory + Goal Loop",
            "mission_title": mission.get("title", "No active mission"),
            "current_focus": mission.get("current_focus", ""),
            "active_goals": len(goals),
            "focus_items": len(focus),
            "speech": companion.get("suggested_speech", ""),
            "goals": goals,
            "focus": focus,
        }
''')

write("buster/ui/widgets/working_memory_goal_widget.py", r'''
try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
except Exception:
    QWidget = object
    QVBoxLayout = None
    QLabel = None

class WorkingMemoryGoalWidget(QWidget):
    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            layout = QVBoxLayout(self)
            self.title = QLabel("Working Memory + Goal Loop")
            self.status = QLabel("No active mission")
            layout.addWidget(self.title)
            layout.addWidget(self.status)
        except Exception:
            self.status = None

    def update_model(self, model):
        text = f"{model.get('mission_title', 'No mission')} | goals: {model.get('active_goals', 0)}"
        if self.status is not None:
            self.status.setText(text)
        return text
''')

write("buster/brain/planner/goal_loop_planner_bridge.py", r'''
from typing import Any, Dict
from buster.mind.work_loop import WorkingMemoryGoalLoop

class GoalLoopPlannerBridge:
    def __init__(self, loop=None):
        self.loop = loop or WorkingMemoryGoalLoop()

    def plan_from_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self.loop.ingest_observation(observation)
        goal = snapshot.get("goals", [{}])[0] if snapshot.get("goals") else {}
        return {
            "should_plan": bool(goal),
            "goal": goal,
            "mission": snapshot.get("mission", {}),
            "companion_context": snapshot.get("companion_context", {}),
        }
''')

# update __init__ safely
write("buster/mind/__init__.py", r'''
try:
    from .engine import MindEngine
except Exception:
    MindEngine = None
from .mission_context import MissionContext, MissionContextManager
from .goal_loop import Goal, GoalLoop
from .context_priority import ContextPrioritizer
from .companion_context import CompanionContextBuilder
from .work_loop import WorkingMemoryGoalLoop
''')

create_json("data/mission_context.json", {"current": None, "history": []})
create_json("data/goal_loop_state.json", {"goals": [], "last_updated": None})
create_json("data/working_memory_goal_loop.json", {"mission": {}, "goals": [], "focus": []})
create_json("data/companion_context.json", {"mode": "companion", "suggested_speech": ""})

print("\nSUCCESS: Buster v5.4 Working Memory + Goal Loop installed.")
print("Next: python test_v5_4_working_memory_goal_loop.py")
