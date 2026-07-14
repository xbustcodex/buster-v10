from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path.cwd()


def write(path, content):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    print(f"[WRITE] {path}")


def create_json(path, data):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(f"[CREATE] {path}")
    else:
        print(f"[SKIP] {path} already exists")

print('=== Applying Buster v4.0 AI OS Core Integration Patch ===')

write('buster/ai_os/__init__.py', '''"""Buster AI OS v4.0 integration package."""
from .status import AIOSStatus
from .context import AIOSContext
from .orchestrator import AIOSOrchestrator
from .facade import BusterAIOS

__all__ = ["AIOSStatus", "AIOSContext", "AIOSOrchestrator", "BusterAIOS"]
''')

write('buster/ai_os/status.py', '''from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AIOSStatus:
    online: bool = True
    mode: str = "standby"
    current_mission: str = "Waiting for command"
    confidence: float = 0.0
    risk: str = "unknown"
    strategy: List[str] = field(default_factory=list)
    active_agents: List[str] = field(default_factory=list)
    plugins_loaded: int = 0
    learning_items: int = 0
    experience_items: int = 0
    events_recorded: int = 0
    updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "online": self.online,
            "mode": self.mode,
            "current_mission": self.current_mission,
            "confidence": self.confidence,
            "risk": self.risk,
            "strategy": list(self.strategy),
            "active_agents": list(self.active_agents),
            "plugins_loaded": self.plugins_loaded,
            "learning_items": self.learning_items,
            "experience_items": self.experience_items,
            "events_recorded": self.events_recorded,
            "updated": self.updated,
        }
''')

write('buster/ai_os/context.py', '''from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AIOSContext:
    root: Path = field(default_factory=lambda: Path.cwd())
    user_request: str = ""
    project_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def data_path(self, name: str) -> Path:
        p = self.root / "data" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
''')

write('buster/ai_os/storage.py', '''import json
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path, default: Any):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def count_items(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("items", "records", "events", "plugins", "experiences", "patterns", "strategies"):
            found = value.get(key)
            if isinstance(found, list):
                return len(found)
            if isinstance(found, dict):
                return len(found)
        return len(value)
    return 0
''')

write('buster/ai_os/planning_pipeline.py', '''from typing import Any, Dict, List


class PlanningPipeline:
    """Small integration layer that turns a user request into one unified AI OS plan."""

    def classify(self, request: str) -> str:
        text = (request or "").lower()
        if any(w in text for w in ("build", "create", "make", "app", "project")):
            return "build"
        if any(w in text for w in ("fix", "error", "bug", "failed", "crash")):
            return "fix"
        if any(w in text for w in ("test", "verify", "check")):
            return "verify"
        if any(w in text for w in ("index", "repo", "repository", "scan")):
            return "repository"
        return "general"

    def strategy_for(self, intent: str) -> List[str]:
        strategies = {
            "build": ["repository", "learning", "experience", "builder", "tester", "reviewer", "verifier", "learning"],
            "fix": ["repository", "experience", "fixer", "tester", "verifier", "learning"],
            "verify": ["tester", "reviewer", "verifier", "experience"],
            "repository": ["repository", "knowledge", "mission_control"],
            "general": ["brain", "planner", "mission_control"],
        }
        return strategies.get(intent, strategies["general"])

    def agents_for(self, intent: str) -> List[str]:
        agents = {
            "build": ["Builder", "Tester", "Reviewer", "Verifier"],
            "fix": ["Fixer", "Tester", "Verifier"],
            "verify": ["Tester", "Reviewer", "Verifier"],
            "repository": ["Repository"],
            "general": ["Planner"],
        }
        return agents.get(intent, agents["general"])

    def make_plan(self, request: str) -> Dict[str, Any]:
        intent = self.classify(request)
        strategy = self.strategy_for(intent)
        agents = self.agents_for(intent)
        return {
            "request": request,
            "intent": intent,
            "strategy": strategy,
            "agents": agents,
            "requires_confirmation": intent in ("fix",) and len(request.strip()) < 12,
        }
''')

write('buster/ai_os/integration.py', '''from typing import Any, Dict


class AIOSIntegration:
    """Connects v3 systems without forcing direct imports everywhere."""

    def __init__(self, context):
        self.context = context

    def summarize(self) -> Dict[str, Any]:
        from .storage import read_json, count_items
        learning = read_json(self.context.data_path("learning_memory.json"), {})
        experience = read_json(self.context.data_path("experience_memory.json"), {})
        events = read_json(self.context.data_path("event_history.json"), {})
        plugins = read_json(self.context.data_path("plugin_registry.json"), {})
        mission = read_json(self.context.data_path("mission_control_dashboard.json"), {})
        return {
            "learning_items": count_items(learning),
            "experience_items": count_items(experience),
            "events_recorded": count_items(events),
            "plugins_loaded": count_items(plugins),
            "mission": mission,
        }
''')

write('buster/ai_os/orchestrator.py', '''from datetime import datetime, timezone
from typing import Any, Dict

from .context import AIOSContext
from .integration import AIOSIntegration
from .planning_pipeline import PlanningPipeline
from .status import AIOSStatus
from .storage import read_json, write_json


class AIOSOrchestrator:
    """Unified Buster AI OS brain glue.

    This does not replace existing modules. It coordinates them into one OS status.
    """

    def __init__(self, context: AIOSContext | None = None):
        self.context = context or AIOSContext()
        self.pipeline = PlanningPipeline()
        self.integration = AIOSIntegration(self.context)

    def plan(self, request: str) -> Dict[str, Any]:
        base_plan = self.pipeline.make_plan(request)
        integrated = self.integration.summarize()
        confidence = self._confidence(base_plan, integrated)
        risk = self._risk(base_plan, confidence)
        plan = {
            **base_plan,
            "confidence": confidence,
            "risk": risk,
            "integrated": integrated,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self._record_event("PLAN_CREATED", plan)
        self._write_status(plan)
        return plan

    def status(self) -> AIOSStatus:
        data = read_json(self.context.data_path("ai_os_status.json"), {})
        if not data:
            integrated = self.integration.summarize()
            return AIOSStatus(
                confidence=0.0,
                plugins_loaded=integrated["plugins_loaded"],
                learning_items=integrated["learning_items"],
                experience_items=integrated["experience_items"],
                events_recorded=integrated["events_recorded"],
            )
        return AIOSStatus(**data)

    def _confidence(self, plan: Dict[str, Any], integrated: Dict[str, Any]) -> float:
        score = 0.55
        if integrated.get("learning_items", 0) > 0:
            score += 0.10
        if integrated.get("experience_items", 0) > 0:
            score += 0.12
        if integrated.get("plugins_loaded", 0) > 0:
            score += 0.08
        if plan.get("intent") in ("build", "fix", "verify"):
            score += 0.08
        if plan.get("requires_confirmation"):
            score -= 0.20
        return round(max(0.0, min(score, 0.99)), 2)

    def _risk(self, plan: Dict[str, Any], confidence: float) -> str:
        if plan.get("requires_confirmation"):
            return "needs_confirmation"
        if confidence >= 0.85:
            return "low"
        if confidence >= 0.65:
            return "medium"
        return "high"

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        path = self.context.data_path("event_history.json")
        history = read_json(path, {"events": []})
        if isinstance(history, list):
            history = {"events": history}
        history.setdefault("events", [])
        history["events"].append({
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "payload": {
                "intent": payload.get("intent"),
                "confidence": payload.get("confidence"),
                "risk": payload.get("risk"),
                "strategy": payload.get("strategy", []),
            },
        })
        history["events"] = history["events"][-250:]
        write_json(path, history)

    def _write_status(self, plan: Dict[str, Any]) -> None:
        integrated = plan.get("integrated", {})
        status = AIOSStatus(
            online=True,
            mode="planning",
            current_mission=plan.get("request") or "Waiting for command",
            confidence=plan.get("confidence", 0.0),
            risk=plan.get("risk", "unknown"),
            strategy=plan.get("strategy", []),
            active_agents=plan.get("agents", []),
            plugins_loaded=integrated.get("plugins_loaded", 0),
            learning_items=integrated.get("learning_items", 0),
            experience_items=integrated.get("experience_items", 0),
            events_recorded=integrated.get("events_recorded", 0),
        )
        write_json(self.context.data_path("ai_os_status.json"), status.as_dict())
        write_json(self.context.data_path("mission_control_unified.json"), {
            "title": "Buster AI OS Mission Control",
            "status": status.as_dict(),
            "plan": plan,
        })
''')

write('buster/ai_os/facade.py', '''from .context import AIOSContext
from .orchestrator import AIOSOrchestrator


class BusterAIOS:
    """Single public entry point for the integrated AI OS layer."""

    def __init__(self, root=None):
        context = AIOSContext(root=root) if root else AIOSContext()
        self.orchestrator = AIOSOrchestrator(context)

    def think(self, request: str):
        return self.orchestrator.plan(request)

    def status(self):
        return self.orchestrator.status().as_dict()
''')

write('buster/workspace/ai_os_unified.py', '''from buster.ai_os import BusterAIOS


class UnifiedAIOSWorkspace:
    """Mission Control friendly wrapper for the v4 AI OS integration."""

    def __init__(self, root=None):
        self.aios = BusterAIOS(root=root)

    def submit_command(self, text: str):
        return self.aios.think(text)

    def get_status(self):
        return self.aios.status()
''')

write('test_v4_0_ai_os_core_integration.py', '''from pathlib import Path
import tempfile

from buster.ai_os import BusterAIOS
from buster.ai_os.planning_pipeline import PlanningPipeline
from buster.workspace.ai_os_unified import UnifiedAIOSWorkspace


def test_pipeline_build_plan():
    pipe = PlanningPipeline()
    plan = pipe.make_plan("build my Android app")
    assert plan["intent"] == "build"
    assert "builder" in [x.lower() for x in plan["strategy"]]
    assert "Builder" in plan["agents"]


def test_aios_status_written():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "data").mkdir()
        aios = BusterAIOS(root=root)
        plan = aios.think("fix this Python crash")
        status = aios.status()
        assert plan["intent"] == "fix"
        assert status["current_mission"] == "fix this Python crash"
        assert (root / "data" / "ai_os_status.json").exists()
        assert (root / "data" / "mission_control_unified.json").exists()


def test_workspace_wrapper():
    with tempfile.TemporaryDirectory() as d:
        ws = UnifiedAIOSWorkspace(root=Path(d))
        plan = ws.submit_command("index repository")
        assert plan["intent"] == "repository"
        assert ws.get_status()["online"] is True


if __name__ == "__main__":
    test_pipeline_build_plan()
    test_aios_status_written()
    test_workspace_wrapper()
    print("SUCCESS: v4.0 AI OS Core Integration tests passed")
''')

create_json('data/ai_os_status.json', {
    "online": True,
    "mode": "standby",
    "current_mission": "Waiting for command",
    "confidence": 0.0,
    "risk": "unknown",
    "strategy": [],
    "active_agents": [],
    "plugins_loaded": 0,
    "learning_items": 0,
    "experience_items": 0,
    "events_recorded": 0,
    "updated": datetime.now(timezone.utc).isoformat(timespec='seconds')
})
create_json('data/mission_control_unified.json', {"title": "Buster AI OS Mission Control", "status": {}, "plan": {}})

print('\nSUCCESS: Buster v4.0 AI OS Core Integration installed.')
print('Next: python test_v4_0_ai_os_core_integration.py')
