
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
