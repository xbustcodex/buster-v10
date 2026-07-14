#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent

def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dedent(content).lstrip(), encoding="utf-8")
    print(f"[WRITE] {path}")

def create_json(path: str, default) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(json.dumps(default, indent=2), encoding="utf-8")
        print(f"[CREATE] {path}")
    else:
        print(f"[KEEP] {path}")

def main() -> None:
    print("=== Applying Buster v3.7 Intelligence Core + Event Bus Patch ===")

    write("buster/intelligence/__init__.py", """
    from .confidence import ConfidenceEngine
    from .risk_analysis import RiskAnalyzer
    from .strategy_selector import StrategySelector
    from .reasoning import ReasoningEngine

    __all__ = [
        "ConfidenceEngine",
        "RiskAnalyzer",
        "StrategySelector",
        "ReasoningEngine",
    ]
    """)

    write("buster/intelligence/confidence.py", """
    from __future__ import annotations

    from dataclasses import dataclass
    from typing import Any, Dict


    @dataclass
    class ConfidenceResult:
        score: float
        level: str
        reason: str
        should_ask_user: bool

        def to_dict(self) -> Dict[str, Any]:
            return {
                "score": self.score,
                "level": self.level,
                "reason": self.reason,
                "should_ask_user": self.should_ask_user,
            }


    class ConfidenceEngine:
        def score(self, signals: Dict[str, Any] | None = None) -> ConfidenceResult:
            signals = signals or {}
            value = 0.65

            if signals.get("tests_passed"):
                value += 0.15
            if signals.get("known_strategy"):
                value += 0.10
            if signals.get("similar_success"):
                value += 0.10
            if signals.get("has_plugin"):
                value += 0.05

            if signals.get("tests_failed"):
                value -= 0.20
            if signals.get("destructive_action"):
                value -= 0.25
            if signals.get("unknown_project"):
                value -= 0.15
            if signals.get("high_risk"):
                value -= 0.20

            value = max(0.0, min(1.0, value))

            if value >= 0.85:
                level = "high"
                reason = "Strong signals found; safe to proceed."
                ask = False
            elif value >= 0.60:
                level = "medium"
                reason = "Enough confidence to prepare a plan, but verify before risky action."
                ask = bool(signals.get("destructive_action") or signals.get("high_risk"))
            else:
                level = "low"
                reason = "Not enough confidence; user confirmation recommended."
                ask = True

            return ConfidenceResult(round(value, 2), level, reason, ask)
    """)

    write("buster/intelligence/risk_analysis.py", """
    from __future__ import annotations

    from dataclasses import dataclass, field
    from typing import Any, Dict, List


    @dataclass
    class RiskReport:
        level: str
        risks: List[str] = field(default_factory=list)
        blockers: List[str] = field(default_factory=list)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "level": self.level,
                "risks": self.risks,
                "blockers": self.blockers,
            }


    class RiskAnalyzer:
        destructive_keywords = {
            "delete", "remove", "wipe", "format", "reset", "overwrite",
            "factory", "flash", "partition", "drop database"
        }

        def analyze(self, request: str = "", context: Dict[str, Any] | None = None) -> RiskReport:
            context = context or {}
            text = (request or "").lower()
            risks: List[str] = []
            blockers: List[str] = []

            if any(word in text for word in self.destructive_keywords):
                risks.append("destructive_action")
            if context.get("production"):
                risks.append("production_environment")
            if context.get("missing_tests"):
                risks.append("missing_tests")
            if context.get("unknown_project"):
                risks.append("unknown_project")
            if context.get("requires_credentials"):
                blockers.append("credentials_required")

            if blockers:
                level = "blocked"
            elif len(risks) >= 2:
                level = "high"
            elif risks:
                level = "medium"
            else:
                level = "low"

            return RiskReport(level, risks, blockers)
    """)

    write("buster/intelligence/strategy_selector.py", """
    from __future__ import annotations

    from dataclasses import dataclass, field
    from typing import Any, Dict, List


    @dataclass
    class Strategy:
        name: str
        steps: List[str] = field(default_factory=list)
        agents: List[str] = field(default_factory=list)
        plugins: List[str] = field(default_factory=list)
        reason: str = ""

        def to_dict(self) -> Dict[str, Any]:
            return {
                "name": self.name,
                "steps": self.steps,
                "agents": self.agents,
                "plugins": self.plugins,
                "reason": self.reason,
            }


    class StrategySelector:
        def select(self, request: str = "", context: Dict[str, Any] | None = None) -> Strategy:
            context = context or {}
            text = (request or "").lower()

            if "android" in text or context.get("project_type") == "android":
                return Strategy(
                    "android_build_verify",
                    ["load_android_plugin", "inspect_project", "build", "test", "fix_if_needed", "verify"],
                    ["builder", "tester", "fixer", "reviewer", "verifier"],
                    ["android"],
                    "Android project detected.",
                )

            if "esp32" in text or "arduino" in text or context.get("project_type") in {"esp32", "arduino"}:
                return Strategy(
                    "embedded_build_verify",
                    ["load_embedded_plugin", "inspect_sketch", "compile", "fix_if_needed", "verify"],
                    ["builder", "tester", "fixer", "verifier"],
                    ["esp32", "arduino"],
                    "Embedded hardware project detected.",
                )

            if "gui" in text or "desktop" in text or "tkinter" in text:
                return Strategy(
                    "desktop_gui_behavioral",
                    ["inspect_project", "build", "run_gui", "behavioral_test", "fix_if_needed", "verify"],
                    ["builder", "tester", "fixer", "reviewer", "verifier"],
                    ["python"],
                    "Desktop GUI task detected.",
                )

            return Strategy(
                "general_safe_build",
                ["inspect", "plan", "build", "test", "fix_if_needed", "review", "verify", "learn"],
                ["builder", "tester", "fixer", "reviewer", "verifier"],
                [],
                "Default safe software build strategy.",
            )
    """)

    write("buster/intelligence/decision_tree.py", """
    from __future__ import annotations

    from typing import Any, Dict


    class DecisionTree:
        def decide(self, confidence: Dict[str, Any], risk: Dict[str, Any]) -> str:
            if risk.get("level") == "blocked":
                return "blocked"
            if confidence.get("should_ask_user"):
                return "ask_user"
            if confidence.get("score", 0) >= 0.85 and risk.get("level") == "low":
                return "auto_execute"
            if confidence.get("score", 0) >= 0.60:
                return "prepare_plan"
            return "ask_user"
    """)

    write("buster/intelligence/scoring.py", """
    from __future__ import annotations

    from typing import Iterable


    def weighted_average(values: Iterable[float]) -> float:
        vals = list(values)
        if not vals:
            return 0.0
        return round(sum(vals) / len(vals), 2)


    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))
    """)

    write("buster/intelligence/reasoning.py", """
    from __future__ import annotations

    from dataclasses import dataclass
    from typing import Any, Dict

    from .confidence import ConfidenceEngine
    from .decision_tree import DecisionTree
    from .risk_analysis import RiskAnalyzer
    from .strategy_selector import StrategySelector


    @dataclass
    class ReasoningResult:
        request: str
        strategy: Dict[str, Any]
        risk: Dict[str, Any]
        confidence: Dict[str, Any]
        decision: str

        def to_dict(self) -> Dict[str, Any]:
            return {
                "request": self.request,
                "strategy": self.strategy,
                "risk": self.risk,
                "confidence": self.confidence,
                "decision": self.decision,
            }


    class ReasoningEngine:
        def __init__(self) -> None:
            self.strategy_selector = StrategySelector()
            self.risk_analyzer = RiskAnalyzer()
            self.confidence_engine = ConfidenceEngine()
            self.decision_tree = DecisionTree()

        def reason(self, request: str, context: Dict[str, Any] | None = None) -> ReasoningResult:
            context = context or {}
            strategy = self.strategy_selector.select(request, context)
            risk = self.risk_analyzer.analyze(request, context)

            signals = dict(context)
            signals["known_strategy"] = bool(strategy.name)
            signals["high_risk"] = risk.level in {"high", "blocked"}
            signals["destructive_action"] = "destructive_action" in risk.risks

            confidence = self.confidence_engine.score(signals)
            decision = self.decision_tree.decide(confidence.to_dict(), risk.to_dict())

            return ReasoningResult(request, strategy.to_dict(), risk.to_dict(), confidence.to_dict(), decision)
    """)

    write("buster/core/event_types.py", """
    from __future__ import annotations

    class EventTypes:
        SYSTEM_STARTED = "system.started"
        SYSTEM_STOPPED = "system.stopped"
        PLAN_CREATED = "planner.plan_created"
        CONFIDENCE_SCORED = "intelligence.confidence_scored"
        RISK_ANALYZED = "intelligence.risk_analyzed"
        AGENT_STARTED = "agent.started"
        AGENT_FINISHED = "agent.finished"
        AGENT_FAILED = "agent.failed"
        BUILD_STARTED = "build.started"
        BUILD_COMPLETED = "build.completed"
        BUILD_FAILED = "build.failed"
        TESTS_STARTED = "tests.started"
        TESTS_PASSED = "tests.passed"
        TESTS_FAILED = "tests.failed"
        LEARNING_RECORDED = "learning.recorded"
        PLUGIN_LOADED = "plugin.loaded"
        REPOSITORY_INDEXED = "repository.indexed"
        AUTONOMY_NEXT_ACTION = "autonomy.next_action"
        MISSION_CONTROL_UPDATED = "mission_control.updated"
    """)

    write("buster/core/event_bus.py", """
    from __future__ import annotations

    import json
    from dataclasses import dataclass, field
    from datetime import datetime
    from pathlib import Path
    from typing import Any, Callable, Dict, List


    @dataclass
    class Event:
        type: str
        payload: Dict[str, Any] = field(default_factory=dict)
        source: str = "buster"
        timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

        def to_dict(self) -> Dict[str, Any]:
            return {"type": self.type, "payload": self.payload, "source": self.source, "timestamp": self.timestamp}


    Subscriber = Callable[[Event], None]


    class EventBus:
        def __init__(self, history_path: str | Path = "data/event_history.json") -> None:
            self.subscribers: Dict[str, List[Subscriber]] = {}
            self.history_path = Path(history_path)
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.history_path.exists():
                self.history_path.write_text("[]", encoding="utf-8")

        def subscribe(self, event_type: str, callback: Subscriber) -> None:
            self.subscribers.setdefault(event_type, []).append(callback)

        def publish(self, event_type: str, payload: Dict[str, Any] | None = None, source: str = "buster") -> Event:
            event = Event(event_type, payload or {}, source)
            self._append_history(event)
            for callback in self.subscribers.get(event_type, []):
                callback(event)
            for callback in self.subscribers.get("*", []):
                callback(event)
            return event

        def history(self, limit: int = 50) -> List[Dict[str, Any]]:
            try:
                items = json.loads(self.history_path.read_text(encoding="utf-8"))
            except Exception:
                items = []
            return items[-limit:]

        def _append_history(self, event: Event) -> None:
            try:
                items = json.loads(self.history_path.read_text(encoding="utf-8"))
                if not isinstance(items, list):
                    items = []
            except Exception:
                items = []
            items.append(event.to_dict())
            self.history_path.write_text(json.dumps(items[-500:], indent=2), encoding="utf-8")
    """)

    write("buster/core/subscribers.py", """
    from __future__ import annotations

    from typing import Any, Dict, List
    from .event_bus import Event
    from .event_types import EventTypes


    class EventRecorder:
        def __init__(self) -> None:
            self.events: List[Dict[str, Any]] = []

        def __call__(self, event: Event) -> None:
            self.events.append(event.to_dict())


    def register_default_subscribers(bus) -> EventRecorder:
        recorder = EventRecorder()
        bus.subscribe("*", recorder)
        return recorder


    def publish_system_started(bus) -> None:
        bus.publish(EventTypes.SYSTEM_STARTED, {"status": "ready"}, source="core")
    """)

    write("buster/workspace/mission_control.py", """
    from __future__ import annotations

    import json
    from datetime import datetime
    from pathlib import Path
    from typing import Any, Dict


    class MissionControl:
        def __init__(self, state_path: str | Path = "data/mission_control_state.json") -> None:
            self.state_path = Path(state_path)
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.state_path.exists():
                self.save(self.default_state())

        def default_state(self) -> Dict[str, Any]:
            return {
                "status": "ready",
                "confidence": 0.0,
                "active_agents": [],
                "running_jobs": [],
                "plugins_loaded": [],
                "learning_entries": 0,
                "last_decision": None,
                "last_strategy": None,
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }

        def load(self) -> Dict[str, Any]:
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            return self.default_state()

        def save(self, data: Dict[str, Any]) -> None:
            data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        def update_from_reasoning(self, reasoning_result: Dict[str, Any]) -> Dict[str, Any]:
            state = self.load()
            state["confidence"] = reasoning_result.get("confidence", {}).get("score", 0.0)
            state["last_decision"] = reasoning_result.get("decision")
            state["last_strategy"] = reasoning_result.get("strategy", {}).get("name")
            self.save(state)
            return state

        def summary(self) -> str:
            state = self.load()
            return (
                "MISSION CONTROL\\n"
                f"Status: {state.get('status')}\\n"
                f"Confidence: {state.get('confidence')}\\n"
                f"Decision: {state.get('last_decision')}\\n"
                f"Strategy: {state.get('last_strategy', 'none')}\\n"
                f"Plugins Loaded: {len(state.get('plugins_loaded', []))}\\n"
                f"Running Jobs: {len(state.get('running_jobs', []))}\\n"
            )
    """)

    create_json("data/intelligence_state.json", {
        "version": "3.7",
        "confidence_thresholds": {"auto_execute": 0.85, "prepare_plan": 0.60, "ask_user": 0.0},
        "last_reasoning": None,
    })
    create_json("data/event_history.json", [])
    create_json("data/mission_control_state.json", {
        "status": "ready",
        "confidence": 0.0,
        "active_agents": [],
        "running_jobs": [],
        "plugins_loaded": [],
        "learning_entries": 0,
        "last_decision": None,
        "last_strategy": None,
        "updated_at": None,
    })

    print()
    print("SUCCESS: Buster v3.7 Intelligence Core + Event Bus installed.")
    print("Next: python test_v3_7_intelligence_event_bus.py")

if __name__ == "__main__":
    main()
