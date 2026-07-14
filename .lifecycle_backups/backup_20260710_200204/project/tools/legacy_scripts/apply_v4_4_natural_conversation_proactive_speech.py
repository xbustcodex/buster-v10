#!/usr/bin/env python3
"""
Buster v4.4 Natural Conversation + Proactive Speech

Adds a safe proactive speech layer so Buster can talk first when important
things happen, while still respecting quiet mode, cooldowns, importance,
and user-controlled talk frequency.
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
    target.write_text(content.lstrip(), encoding="utf-8")
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
    print("=== Applying Buster v4.4 Natural Conversation + Proactive Speech Patch ===")

    write("buster/conversation_os/__init__.py", r'''
from .modes import TalkMode, SpeechPriority
from .settings import ProactiveSpeechSettings
from .speech_queue import SpeechQueue
from .speech_scheduler import ProactiveSpeechScheduler
from .explanations import DecisionExplainer
from .natural_conversation import NaturalConversationEngine
from .mission_voice import MissionVoiceBridge
from .engine import ConversationOS

__all__ = [
    "TalkMode",
    "SpeechPriority",
    "ProactiveSpeechSettings",
    "SpeechQueue",
    "ProactiveSpeechScheduler",
    "DecisionExplainer",
    "NaturalConversationEngine",
    "MissionVoiceBridge",
    "ConversationOS",
]
''')

    write("buster/conversation_os/modes.py", r'''
from __future__ import annotations


class TalkMode:
    SILENT = "silent"
    QUIET = "quiet"
    BALANCED = "balanced"
    TALKATIVE = "talkative"
    JARVIS = "jarvis"


class SpeechPriority:
    LOW = "low"
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"


PRIORITY_SCORE = {
    SpeechPriority.LOW: 1,
    SpeechPriority.NORMAL: 2,
    SpeechPriority.IMPORTANT: 3,
    SpeechPriority.URGENT: 4,
}
''')

    write("buster/conversation_os/settings.py", r'''
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any

from .modes import TalkMode


DEFAULT_SETTINGS = {
    "enabled": True,
    "mode": TalkMode.BALANCED,
    "quiet_mode": False,
    "speak_agent_updates": True,
    "speak_mission_events": True,
    "speak_decisions": True,
    "speak_errors": True,
    "speak_success": True,
    "min_priority": "normal",
    "cooldown_seconds": 20,
    "max_items_per_hour": 18,
    "allow_idle_checkins": True,
    "idle_checkin_minutes": 30,
}


@dataclass
class ProactiveSpeechSettings:
    path: str = "data/proactive_speech_settings.json"

    def load(self) -> Dict[str, Any]:
        target = Path(self.path)
        if not target.exists():
            return dict(DEFAULT_SETTINGS)
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data if isinstance(data, dict) else {})
        return merged

    def save(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        data = self.load()
        data.update(updates)
        target = Path(self.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def set_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in {TalkMode.SILENT, TalkMode.QUIET, TalkMode.BALANCED, TalkMode.TALKATIVE, TalkMode.JARVIS}:
            raise ValueError(f"Unknown talk mode: {mode}")
        updates = {"mode": mode, "enabled": mode != TalkMode.SILENT}
        if mode == TalkMode.QUIET:
            updates.update({"cooldown_seconds": 60, "max_items_per_hour": 6, "min_priority": "important"})
        elif mode == TalkMode.BALANCED:
            updates.update({"cooldown_seconds": 20, "max_items_per_hour": 18, "min_priority": "normal"})
        elif mode == TalkMode.TALKATIVE:
            updates.update({"cooldown_seconds": 8, "max_items_per_hour": 40, "min_priority": "low"})
        elif mode == TalkMode.JARVIS:
            updates.update({"cooldown_seconds": 5, "max_items_per_hour": 60, "min_priority": "low", "allow_idle_checkins": True})
        return self.save(updates)
''')

    write("buster/conversation_os/speech_queue.py", r'''
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SpeechQueue:
    def __init__(self, path: str = "data/proactive_speech_queue.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, items: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(items[-500:], indent=2), encoding="utf-8")

    def add(self, text: str, priority: str = "normal", source: str = "buster", reason: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex[:12],
            "text": text,
            "priority": priority,
            "source": source,
            "reason": reason,
            "metadata": metadata or {},
            "created": utc_now(),
            "spoken": False,
            "spoken_at": None,
        }
        items = self._load()
        items.append(item)
        self._save(items)
        return item

    def pending(self) -> List[Dict[str, Any]]:
        return [i for i in self._load() if not i.get("spoken")]

    def mark_spoken(self, item_id: str) -> bool:
        items = self._load()
        changed = False
        for item in items:
            if item.get("id") == item_id:
                item["spoken"] = True
                item["spoken_at"] = utc_now()
                changed = True
                break
        self._save(items)
        return changed

    def clear(self) -> None:
        self._save([])
''')

    write("buster/conversation_os/speech_scheduler.py", r'''
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .modes import PRIORITY_SCORE
from .settings import ProactiveSpeechSettings
from .speech_queue import SpeechQueue


def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


class ProactiveSpeechScheduler:
    def __init__(self, queue: SpeechQueue | None = None, settings: ProactiveSpeechSettings | None = None) -> None:
        self.queue = queue or SpeechQueue()
        self.settings = settings or ProactiveSpeechSettings()

    def should_speak(self, item: Dict[str, Any], history: List[Dict[str, Any]] | None = None) -> tuple[bool, str]:
        cfg = self.settings.load()
        if not cfg.get("enabled", True):
            return False, "proactive speech disabled"
        if cfg.get("quiet_mode", False) and item.get("priority") != "urgent":
            return False, "quiet mode active"
        min_priority = cfg.get("min_priority", "normal")
        if PRIORITY_SCORE.get(item.get("priority", "normal"), 2) < PRIORITY_SCORE.get(min_priority, 2):
            return False, "below priority threshold"

        history = history or []
        now = datetime.now(timezone.utc)
        spoken_times = [parse_time(h.get("spoken_at")) for h in history if h.get("spoken_at")]
        spoken_times = [t for t in spoken_times if t is not None]

        if spoken_times:
            last = max(spoken_times)
            if (now - last).total_seconds() < int(cfg.get("cooldown_seconds", 20)) and item.get("priority") != "urgent":
                return False, "cooldown active"

        hour_count = sum(1 for t in spoken_times if now - t < timedelta(hours=1))
        if hour_count >= int(cfg.get("max_items_per_hour", 18)) and item.get("priority") != "urgent":
            return False, "hourly speech limit reached"

        return True, "allowed"

    def next_item(self) -> Dict[str, Any] | None:
        pending = self.queue.pending()
        if not pending:
            return None
        all_items = self.queue._load()
        pending.sort(key=lambda i: PRIORITY_SCORE.get(i.get("priority", "normal"), 2), reverse=True)
        for item in pending:
            ok, reason = self.should_speak(item, all_items)
            if ok:
                item["scheduler_reason"] = reason
                return item
        return None

    def pop_next_for_speech(self) -> Dict[str, Any] | None:
        item = self.next_item()
        if not item:
            return None
        self.queue.mark_spoken(item["id"])
        return item
''')

    write("buster/conversation_os/explanations.py", r'''
from __future__ import annotations

from typing import Dict, Any


class DecisionExplainer:
    def explain(self, decision: Dict[str, Any]) -> str:
        action = decision.get("action") or decision.get("event") or "decision"
        confidence = decision.get("confidence")
        risk = decision.get("risk")
        reason = decision.get("reason") or decision.get("why") or "based on the current mission context"
        parts = [f"I chose {action}"]
        if confidence is not None:
            try:
                parts.append(f"with {float(confidence) * 100:.0f}% confidence")
            except Exception:
                parts.append(f"with confidence {confidence}")
        if risk:
            parts.append(f"and {risk} risk")
        parts.append(f"because {reason}.")
        return " ".join(parts)

    def explain_event(self, event: Dict[str, Any]) -> str:
        actor = event.get("actor") or event.get("source") or "Buster"
        title = event.get("title") or event.get("event") or event.get("type") or "updated the mission"
        message = event.get("message") or event.get("description") or ""
        if message:
            return f"{actor}: {title}. {message}"
        return f"{actor}: {title}."
''')

    write("buster/conversation_os/natural_conversation.py", r'''
from __future__ import annotations

from typing import Dict, Any, List


class NaturalConversationEngine:
    def __init__(self) -> None:
        self.openers = {
            "mission_started": "I've started the mission.",
            "planner_created": "I've created a plan.",
            "tests_failed": "The Tester found a problem.",
            "fix_started": "I'm asking the Fixer to investigate.",
            "mission_complete": "Mission complete.",
            "learning_recorded": "I learned something useful from this.",
        }

    def respond_to_event(self, event: Dict[str, Any]) -> str:
        key = str(event.get("event") or event.get("type") or "").lower()
        base = self.openers.get(key, event.get("title") or "I've updated the mission.")
        detail = event.get("message") or event.get("summary") or ""
        confidence = event.get("confidence")
        risk = event.get("risk")
        extras: List[str] = []
        if confidence is not None:
            try:
                extras.append(f"Confidence is {float(confidence) * 100:.0f}%.")
            except Exception:
                pass
        if risk:
            extras.append(f"Risk is {risk}.")
        return " ".join([p for p in [base, detail, *extras] if p]).strip()

    def answer_why(self, context: Dict[str, Any]) -> str:
        reason = context.get("reason") or context.get("why") or "it matched the safest current strategy"
        action = context.get("action") or "that action"
        confidence = context.get("confidence")
        if confidence is not None:
            try:
                return f"I did {action} because {reason}. My confidence was {float(confidence) * 100:.0f}%."
            except Exception:
                pass
        return f"I did {action} because {reason}."

    def idle_checkin(self, status: Dict[str, Any]) -> str:
        mission = status.get("current_mission") or "no active mission"
        active_agents = status.get("active_agents", 0)
        return f"I'm still here. Current mission: {mission}. Active agents: {active_agents}."
''')

    write("buster/conversation_os/mission_voice.py", r'''
from __future__ import annotations

from typing import Dict, Any

from .speech_queue import SpeechQueue
from .natural_conversation import NaturalConversationEngine
from .explanations import DecisionExplainer


class MissionVoiceBridge:
    def __init__(self, queue: SpeechQueue | None = None) -> None:
        self.queue = queue or SpeechQueue()
        self.conversation = NaturalConversationEngine()
        self.explainer = DecisionExplainer()

    def on_mission_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        text = self.conversation.respond_to_event(event)
        priority = event.get("priority") or self._priority_for_event(event)
        return self.queue.add(text, priority=priority, source="mission_control", reason="mission event", metadata=event)

    def on_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        text = self.explainer.explain(decision)
        priority = decision.get("priority") or "important"
        return self.queue.add(text, priority=priority, source="decision_engine", reason="decision explanation", metadata=decision)

    def on_error(self, message: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self.queue.add(message, priority="urgent", source="error_monitor", reason="error", metadata=metadata or {})

    def _priority_for_event(self, event: Dict[str, Any]) -> str:
        name = str(event.get("event") or event.get("type") or "").lower()
        if "error" in name or "failed" in name:
            return "urgent"
        if "complete" in name or "decision" in name or "fix" in name:
            return "important"
        return "normal"
''')

    write("buster/conversation_os/engine.py", r'''
from __future__ import annotations

from typing import Dict, Any

from .settings import ProactiveSpeechSettings
from .speech_queue import SpeechQueue
from .speech_scheduler import ProactiveSpeechScheduler
from .mission_voice import MissionVoiceBridge
from .natural_conversation import NaturalConversationEngine
from .explanations import DecisionExplainer


class ConversationOS:
    def __init__(self) -> None:
        self.settings = ProactiveSpeechSettings()
        self.queue = SpeechQueue()
        self.scheduler = ProactiveSpeechScheduler(self.queue, self.settings)
        self.mission_voice = MissionVoiceBridge(self.queue)
        self.natural = NaturalConversationEngine()
        self.explainer = DecisionExplainer()

    def configure(self, **updates: Any) -> Dict[str, Any]:
        return self.settings.save(dict(updates))

    def set_talk_mode(self, mode: str) -> Dict[str, Any]:
        return self.settings.set_mode(mode)

    def mission_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return self.mission_voice.on_mission_event(event)

    def decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        return self.mission_voice.on_decision(decision)

    def say(self, text: str, priority: str = "normal", reason: str = "manual") -> Dict[str, Any]:
        return self.queue.add(text, priority=priority, source="conversation_os", reason=reason)

    def next_speech(self) -> Dict[str, Any] | None:
        return self.scheduler.pop_next_for_speech()

    def why(self, context: Dict[str, Any]) -> str:
        return self.natural.answer_why(context)

    def status(self) -> Dict[str, Any]:
        return {
            "settings": self.settings.load(),
            "pending_speech": len(self.queue.pending()),
        }
''')

    write("buster/collaboration/proactive_voice_runtime.py", r'''
from __future__ import annotations

from typing import Dict, Any

try:
    from buster.conversation_os import ConversationOS
except Exception:  # pragma: no cover
    ConversationOS = None  # type: ignore


class ProactiveVoiceRuntime:
    """Runtime adapter that lets collaboration feed Buster's natural speech layer."""

    def __init__(self) -> None:
        if ConversationOS is None:
            raise RuntimeError("ConversationOS is not available")
        self.os = ConversationOS()

    def agent_update(self, agent: str, status: str, message: str = "", confidence: float | None = None, risk: str | None = None) -> Dict[str, Any]:
        event = {
            "event": "agent_update",
            "actor": agent,
            "title": f"{agent} is {status}",
            "message": message,
            "confidence": confidence,
            "risk": risk,
            "priority": "normal" if status not in {"error", "failed"} else "urgent",
        }
        return self.os.mission_event(event)

    def speak_next(self) -> Dict[str, Any] | None:
        return self.os.next_speech()
''')

    write("buster/brain/planner/conversation_planner_bridge.py", r'''
from __future__ import annotations

from typing import Dict, Any

try:
    from buster.conversation_os import ConversationOS
except Exception:  # pragma: no cover
    ConversationOS = None  # type: ignore


class ConversationPlannerBridge:
    def __init__(self) -> None:
        if ConversationOS is None:
            raise RuntimeError("ConversationOS is not available")
        self.conversation = ConversationOS()

    def announce_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "event": "planner_created",
            "actor": "Planner",
            "title": "Planner created a mission plan",
            "message": plan.get("summary") or plan.get("goal") or "I have a strategy ready.",
            "confidence": plan.get("confidence"),
            "risk": plan.get("risk"),
            "priority": "important",
        }
        return self.conversation.mission_event(event)

    def explain_plan(self, plan: Dict[str, Any]) -> str:
        return self.conversation.why({
            "action": plan.get("strategy") or "this plan",
            "reason": plan.get("reason") or "it best matches the current mission context and past experience",
            "confidence": plan.get("confidence"),
        })
''')

    write("buster/workspace/proactive_speech_dashboard.py", r'''
from __future__ import annotations

from typing import Dict, Any

try:
    from buster.conversation_os import ConversationOS
except Exception:  # pragma: no cover
    ConversationOS = None  # type: ignore


class ProactiveSpeechDashboard:
    def __init__(self) -> None:
        self.os = ConversationOS() if ConversationOS is not None else None

    def snapshot(self) -> Dict[str, Any]:
        if self.os is None:
            return {"available": False, "pending_speech": 0, "mode": "unknown"}
        status = self.os.status()
        settings = status.get("settings", {})
        return {
            "available": True,
            "enabled": settings.get("enabled"),
            "mode": settings.get("mode"),
            "quiet_mode": settings.get("quiet_mode"),
            "pending_speech": status.get("pending_speech", 0),
            "cooldown_seconds": settings.get("cooldown_seconds"),
            "max_items_per_hour": settings.get("max_items_per_hour"),
        }
''')

    write("buster/ui/widgets/proactive_speech_widget.py", r'''
from __future__ import annotations

from typing import Dict, Any

try:
    from buster.workspace.proactive_speech_dashboard import ProactiveSpeechDashboard
except Exception:  # pragma: no cover
    ProactiveSpeechDashboard = None  # type: ignore


class ProactiveSpeechWidgetModel:
    def __init__(self) -> None:
        self.dashboard = ProactiveSpeechDashboard() if ProactiveSpeechDashboard is not None else None

    def render_model(self) -> Dict[str, Any]:
        if self.dashboard is None:
            return {"title": "Proactive Speech", "available": False}
        snap = self.dashboard.snapshot()
        return {
            "title": "Proactive Speech",
            "subtitle": "Buster can speak first when important things happen.",
            **snap,
        }
''')

    write("buster/conversation_os/README.md", r'''
# Buster v4.4 Natural Conversation + Proactive Speech

This layer lets Buster talk first without becoming annoying.

It provides:

- proactive speech queue
- background scheduler logic
- quiet mode
- talk frequency modes
- decision explanations
- Mission Control voice bridge
- "why did you do that?" answers

Talk modes:

- silent
- quiet
- balanced
- talkative
- jarvis

The speech queue stores what Buster wants to say. The scheduler decides when it is safe and useful to say it.
''')

    # Data files
    create_json("data/proactive_speech_settings.json", {
        "enabled": True,
        "mode": "balanced",
        "quiet_mode": False,
        "speak_agent_updates": True,
        "speak_mission_events": True,
        "speak_decisions": True,
        "speak_errors": True,
        "speak_success": True,
        "min_priority": "normal",
        "cooldown_seconds": 20,
        "max_items_per_hour": 18,
        "allow_idle_checkins": True,
        "idle_checkin_minutes": 30,
        "updated": utc_now(),
    })
    create_json("data/proactive_speech_queue.json", [])
    create_json("data/conversation_os_state.json", {
        "version": "4.4",
        "status": "ready",
        "last_speech": None,
        "pending_speech": 0,
        "updated": utc_now(),
    })
    create_json("data/decision_explanations.json", [])
    create_json("data/natural_conversation_memory.json", [])

    print("\nSUCCESS: Buster v4.4 Natural Conversation + Proactive Speech installed.")
    print("Next: python test_v4_4_natural_conversation_proactive_speech.py")


if __name__ == "__main__":
    main()
