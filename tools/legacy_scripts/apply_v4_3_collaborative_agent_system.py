#!/usr/bin/env python3
"""
Buster v4.3 Collaborative Agent System + Proactive Voice Presence
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"[WRITE] {path}")


def create_json(path: str, data) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"[SKIP] {path}")
        return
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[CREATE] {path}")


def main() -> None:
    print("=== Applying Buster v4.3 Collaborative Agent System Patch ===")

    write("buster/collaboration/__init__.py", """
from .agent_state import AgentState, AgentStatus
from .activity_feed import AgentActivityFeed
from .conversation import AgentConversation
from .proactive_voice import ProactiveVoicePresence
from .engine import CollaborativeAgentEngine

__all__ = [
    "AgentState",
    "AgentStatus",
    "AgentActivityFeed",
    "AgentConversation",
    "ProactiveVoicePresence",
    "CollaborativeAgentEngine",
]
""")

    write("buster/collaboration/agent_state.py", """
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AgentStatus:
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    LEARNING = "learning"
    BUILDING = "building"
    TESTING = "testing"
    FIXING = "fixing"
    REVIEWING = "reviewing"
    VERIFYING = "verifying"
    MONITORING = "monitoring"
    WAITING = "waiting"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class AgentState:
    name: str
    role: str
    status: str = AgentStatus.IDLE
    message: str = ""
    confidence: float = 0.0
    risk: str = "unknown"
    updated: str = ""

    def __post_init__(self) -> None:
        if not self.updated:
            self.updated = utc_now()

    def update(self, status: str, message: str = "", confidence: float | None = None, risk: str | None = None) -> "AgentState":
        self.status = status
        self.message = message
        if confidence is not None:
            self.confidence = max(0.0, min(1.0, float(confidence)))
        if risk is not None:
            self.risk = risk
        self.updated = utc_now()
        return self

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
""")

    write("buster/collaboration/activity_feed.py", """
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AgentActivityFeed:
    def __init__(self, path: str | Path = "data/agent_activity_feed.json", limit: int = 250):
        self.path = Path(path)
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write(self, events: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(events[-self.limit:], indent=2), encoding="utf-8")

    def record(self, agent: str, status: str, message: str, confidence: float = 0.0, risk: str = "unknown", mission_id: str = "default") -> Dict[str, Any]:
        item = {
            "time": utc_now(),
            "mission_id": mission_id,
            "agent": agent,
            "status": status,
            "message": message,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "risk": risk,
        }
        events = self._read()
        events.append(item)
        self._write(events)
        return item

    def latest(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._read()[-limit:]
""")

    write("buster/collaboration/conversation.py", """
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AgentConversation:
    def __init__(self, path: str | Path = "data/agent_conversation.json", limit: int = 250):
        self.path = Path(path)
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write(self, messages: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(messages[-self.limit:], indent=2), encoding="utf-8")

    def say(self, speaker: str, text: str, reason: str = "", confidence: float = 0.0, mission_id: str = "default", visible_to_user: bool = True) -> Dict[str, Any]:
        item = {
            "time": utc_now(),
            "mission_id": mission_id,
            "speaker": speaker,
            "text": text,
            "reason": reason,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "visible_to_user": bool(visible_to_user),
        }
        messages = self._read()
        messages.append(item)
        self._write(messages)
        return item

    def latest(self, limit: int = 20, user_visible_only: bool = False) -> List[Dict[str, Any]]:
        messages = self._read()
        if user_visible_only:
            messages = [m for m in messages if m.get("visible_to_user", True)]
        return messages[-limit:]
""")

    write("buster/collaboration/proactive_voice.py", """
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProactiveVoicePresence:
    def __init__(self, path: str | Path = "data/proactive_voice_queue.json", settings_path: str | Path = "data/proactive_voice_settings.json"):
        self.path = Path(path)
        self.settings_path = Path(settings_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")
        if not self.settings_path.exists():
            self.settings_path.write_text(json.dumps({
                "enabled": True,
                "quiet_mode": False,
                "talk_when_idle": True,
                "talk_on_mission_events": True,
                "minimum_priority": "normal",
                "updated": utc_now(),
            }, indent=2), encoding="utf-8")

    def settings(self) -> Dict[str, Any]:
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            return {"enabled": True, "quiet_mode": False}

    def set_enabled(self, enabled: bool) -> Dict[str, Any]:
        data = self.settings()
        data["enabled"] = bool(enabled)
        data["updated"] = utc_now()
        self.settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def _read_queue(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_queue(self, queue: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(queue[-200:], indent=2), encoding="utf-8")

    def speak(self, text: str, reason: str = "", priority: str = "normal", confidence: float = 0.0, interrupt: bool = False) -> Dict[str, Any]:
        settings = self.settings()
        item = {
            "time": utc_now(),
            "text": text,
            "reason": reason,
            "priority": priority,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "interrupt": bool(interrupt),
            "enabled": bool(settings.get("enabled", True)) and not bool(settings.get("quiet_mode", False)),
            "spoken": False,
        }
        queue = self._read_queue()
        queue.append(item)
        self._write_queue(queue)
        return item

    def pending(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [m for m in self._read_queue() if not m.get("spoken", False)][-limit:]

    def mark_spoken(self, index: int) -> None:
        queue = self._read_queue()
        if 0 <= index < len(queue):
            queue[index]["spoken"] = True
            queue[index]["spoken_at"] = utc_now()
            self._write_queue(queue)
""")

    write("buster/collaboration/engine.py", """
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

from .agent_state import AgentState, AgentStatus
from .activity_feed import AgentActivityFeed
from .conversation import AgentConversation
from .proactive_voice import ProactiveVoicePresence


DEFAULT_AGENTS = {
    "Planner": "creates missions and chooses strategies",
    "Builder": "builds files and project structure",
    "Tester": "runs tests and finds failures",
    "Fixer": "repairs errors and failed tests",
    "Reviewer": "checks quality and design",
    "Verifier": "confirms the mission is complete",
    "Learning": "records reusable lessons",
    "Experience": "updates skills and project knowledge",
}


class CollaborativeAgentEngine:
    def __init__(self, state_path: str | Path = "data/collaborative_agents_state.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.feed = AgentActivityFeed()
        self.conversation = AgentConversation()
        self.voice = ProactiveVoicePresence()
        self.agents: Dict[str, AgentState] = {}
        self._load_or_init()

    def _load_or_init(self) -> None:
        if self.state_path.exists():
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
                for name, info in raw.get("agents", {}).items():
                    self.agents[name] = AgentState(**info)
                if self.agents:
                    return
            except Exception:
                pass
        self.agents = {name: AgentState(name=name, role=role) for name, role in DEFAULT_AGENTS.items()}
        self.save()

    def save(self) -> None:
        data = {
            "agents": {name: state.to_dict() for name, state in self.agents.items()},
            "active_count": len([a for a in self.agents.values() if a.status != AgentStatus.IDLE]),
        }
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def set_agent_state(self, agent: str, status: str, message: str = "", confidence: float = 0.0, risk: str = "unknown", mission_id: str = "default", talk: bool = False) -> Dict[str, Any]:
        if agent not in self.agents:
            self.agents[agent] = AgentState(name=agent, role="custom agent")
        self.agents[agent].update(status=status, message=message, confidence=confidence, risk=risk)
        self.save()
        event = self.feed.record(agent, status, message, confidence, risk, mission_id)
        self.conversation.say(agent, message or f"{agent} is {status}.", reason=f"Agent state changed to {status}.", confidence=confidence, mission_id=mission_id)
        if talk:
            self.voice.speak(text=message or f"{agent} is {status}.", reason=f"{agent} changed state to {status}.", priority="normal", confidence=confidence)
        return event

    def mission_story_demo(self, mission_id: str = "demo") -> List[Dict[str, Any]]:
        events = []
        events.append(self.set_agent_state("Planner", AgentStatus.PLANNING, "Mission created.", 0.92, "low", mission_id, True))
        events.append(self.set_agent_state("Builder", AgentStatus.BUILDING, "Generating project structure.", 0.88, "medium", mission_id))
        events.append(self.set_agent_state("Tester", AgentStatus.TESTING, "Running tests.", 0.84, "medium", mission_id))
        events.append(self.set_agent_state("Fixer", AgentStatus.FIXING, "Applying previous solution from Experience Engine.", 0.91, "low", mission_id, True))
        events.append(self.set_agent_state("Verifier", AgentStatus.VERIFYING, "Mission verified successfully.", 0.97, "low", mission_id, True))
        events.append(self.set_agent_state("Learning", AgentStatus.LEARNING, "Recorded a reusable success pattern.", 0.95, "low", mission_id))
        events.append(self.set_agent_state("Experience", AgentStatus.LEARNING, "Updated skill profile for this project type.", 0.93, "low", mission_id))
        return events

    def dashboard(self) -> Dict[str, Any]:
        active = [a.to_dict() for a in self.agents.values() if a.status != AgentStatus.IDLE]
        face = "thinking" if any(a["status"] in ("thinking", "planning") for a in active) else "working" if active else "idle"
        return {
            "agents": {name: state.to_dict() for name, state in self.agents.items()},
            "active_agents": active,
            "latest_activity": self.feed.latest(15),
            "latest_conversation": self.conversation.latest(15, user_visible_only=True),
            "pending_voice": self.voice.pending(5),
            "face_expression": face,
        }
""")

    write("buster/collaboration/event_bridge.py", """
from __future__ import annotations

from typing import Any, Dict

from .engine import CollaborativeAgentEngine


class CollaborationEventBridge:
    def __init__(self, engine: CollaborativeAgentEngine | None = None):
        self.engine = engine or CollaborativeAgentEngine()

    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any] | None:
        event_type = str(event.get("type", "")).lower()
        payload = event.get("payload", {}) or {}
        agent = payload.get("agent") or self._agent_from_event(event_type)
        if not agent:
            return None
        status = payload.get("status") or self._status_from_event(event_type)
        message = payload.get("message") or event.get("message") or f"{agent} handled {event_type}."
        confidence = float(payload.get("confidence", event.get("confidence", 0.0)) or 0.0)
        risk = payload.get("risk", event.get("risk", "unknown"))
        mission_id = payload.get("mission_id", event.get("mission_id", "default"))
        talk = bool(payload.get("talk", event.get("talk", False)))
        return self.engine.set_agent_state(agent, status, message, confidence, risk, mission_id, talk)

    def _agent_from_event(self, event_type: str) -> str:
        if "plan" in event_type:
            return "Planner"
        if "build" in event_type:
            return "Builder"
        if "test" in event_type:
            return "Tester"
        if "fix" in event_type:
            return "Fixer"
        if "review" in event_type:
            return "Reviewer"
        if "verify" in event_type:
            return "Verifier"
        if "learn" in event_type:
            return "Learning"
        if "experience" in event_type:
            return "Experience"
        return ""

    def _status_from_event(self, event_type: str) -> str:
        if "fail" in event_type or "error" in event_type:
            return "error"
        if "complete" in event_type or "success" in event_type or "passed" in event_type:
            return "complete"
        if "test" in event_type:
            return "testing"
        if "fix" in event_type:
            return "fixing"
        if "review" in event_type:
            return "reviewing"
        if "verify" in event_type:
            return "verifying"
        if "learn" in event_type or "experience" in event_type:
            return "learning"
        if "plan" in event_type:
            return "planning"
        if "build" in event_type:
            return "building"
        return "thinking"
""")

    write("buster/workspace/collaboration_dashboard.py", """
from __future__ import annotations

from typing import Dict, Any

from buster.collaboration.engine import CollaborativeAgentEngine


class CollaborationDashboard:
    def __init__(self, engine: CollaborativeAgentEngine | None = None):
        self.engine = engine or CollaborativeAgentEngine()

    def snapshot(self) -> Dict[str, Any]:
        data = self.engine.dashboard()
        return {
            "title": "Collaborative Agent System",
            "face_expression": data["face_expression"],
            "active_agents": data["active_agents"],
            "latest_activity": data["latest_activity"],
            "agent_conversation": data["latest_conversation"],
            "pending_voice": data["pending_voice"],
        }
""")

    write("buster/ui/widgets/agent_collaboration_widget.py", """
from __future__ import annotations

from typing import Dict, Any, List


class AgentCollaborationWidgetModel:
    def render_model(self, dashboard_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        agents: List[Dict[str, Any]] = dashboard_snapshot.get("active_agents", [])
        return {
            "title": dashboard_snapshot.get("title", "Collaborative Agent System"),
            "face_expression": dashboard_snapshot.get("face_expression", "idle"),
            "active_count": len(agents),
            "agents": agents,
            "activity": dashboard_snapshot.get("latest_activity", []),
            "conversation": dashboard_snapshot.get("agent_conversation", []),
            "voice_queue": dashboard_snapshot.get("pending_voice", []),
        }
""")

    write("buster/brain/planner/collaboration_planner_bridge.py", """
from __future__ import annotations

from typing import Dict, Any

from buster.collaboration.engine import CollaborativeAgentEngine


class CollaborationPlannerBridge:
    def __init__(self, engine: CollaborativeAgentEngine | None = None):
        self.engine = engine or CollaborativeAgentEngine()

    def announce_plan(self, mission: str, confidence: float = 0.0, risk: str = "unknown") -> Dict[str, Any]:
        return self.engine.set_agent_state("Planner", "planning", f"Mission created: {mission}", confidence=confidence, risk=risk, mission_id=mission, talk=True)

    def announce_decision(self, agent: str, decision: str, reason: str, confidence: float, risk: str = "unknown") -> Dict[str, Any]:
        message = f"{decision} Reason: {reason}"
        return self.engine.set_agent_state(agent, "thinking", message, confidence=confidence, risk=risk, mission_id="decision", talk=True)
""")

    write("buster/collaboration/README.md", """
# Buster v4.3 Collaborative Agent System

Planner -> Agents -> Event Bridge -> Timeline -> Face -> Voice -> Mission Control

Buster can now generate speakable messages even when the user did not talk first.
The actual voice engine can consume `data/proactive_voice_queue.json`.
""")

    create_json("data/collaborative_agents_state.json", {"agents": {}, "active_count": 0, "created": utc_now()})
    create_json("data/agent_activity_feed.json", [])
    create_json("data/agent_conversation.json", [])
    create_json("data/proactive_voice_queue.json", [])
    create_json("data/proactive_voice_settings.json", {
        "enabled": True,
        "quiet_mode": False,
        "talk_when_idle": True,
        "talk_on_mission_events": True,
        "minimum_priority": "normal",
        "updated": utc_now(),
    })

    print()
    print("SUCCESS: Buster v4.3 Collaborative Agent System installed.")
    print("Next: python test_v4_3_collaborative_agent_system.py")


if __name__ == "__main__":
    main()
