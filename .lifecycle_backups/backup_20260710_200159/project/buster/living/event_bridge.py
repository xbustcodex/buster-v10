from __future__ import annotations

from typing import Any, Dict
from .live_timeline import LiveMissionTimeline
from .mission_events import MissionEventType

class MissionTimelineEventBridge:
    """Connects Buster's Event Bus to the Living OS mission timeline."""
    def __init__(self, timeline: LiveMissionTimeline | None = None):
        self.timeline = timeline or LiveMissionTimeline()

    def handle(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_type = str(event.get("type") or event.get("event_type") or event.get("name") or "system.event")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else event
        mission_id = str(payload.get("mission_id", event.get("mission_id", "default")))
        message = payload.get("message") or payload.get("summary") or payload.get("description")
        source = payload.get("source") or event.get("source")
        agent = payload.get("agent") or event.get("agent")
        level = str(payload.get("level", event.get("level", "info")))
        confidence = payload.get("confidence", event.get("confidence"))
        risk = payload.get("risk", event.get("risk", "unknown"))
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        if not details:
            details = {k: v for k, v in payload.items() if k not in {"message", "summary", "description", "source", "agent", "level", "confidence", "risk", "mission_id"}}
        return self.timeline.record(event_type, message, source=source, mission_id=mission_id, level=level, confidence=confidence, risk=risk, agent=agent, details=details)

    def subscribe_to(self, bus: Any) -> bool:
        for method_name in ("subscribe", "on", "add_listener"):
            method = getattr(bus, method_name, None)
            if callable(method):
                try:
                    method(self.handle)
                    return True
                except TypeError:
                    try:
                        method("*", self.handle)
                        return True
                    except TypeError:
                        continue
        return False

    def demo_sequence(self, mission: str = "Example build", project: str = "example_project") -> None:
        self.handle({"type": MissionEventType.PLANNER_CREATED_MISSION, "payload": {"message": f"created mission: {mission}", "confidence": 0.91, "risk": "low"}})
        self.handle({"type": MissionEventType.REPOSITORY_INDEXED, "payload": {"message": f"indexed project: {project}"}})
        self.handle({"type": MissionEventType.BUILDER_GENERATED_CODE, "payload": {"message": "generated code: main.py"}})
        self.handle({"type": MissionEventType.TESTER_FOUND_FAILURE, "payload": {"message": "found 1 failure", "level": "warning", "risk": "medium"}})
        self.handle({"type": MissionEventType.FIXER_REPAIRED_ISSUE, "payload": {"message": "repaired import error", "confidence": 0.82, "risk": "low"}})
        self.handle({"type": MissionEventType.VERIFIER_APPROVED_BUILD, "payload": {"message": "approved build", "confidence": 0.94, "risk": "low"}})
        self.handle({"type": MissionEventType.LEARNING_RECORDED_PATTERN, "payload": {"message": "recorded new pattern: safe import guard"}})
        self.handle({"type": MissionEventType.EXPERIENCE_UPDATED_SKILL, "payload": {"message": "updated Python skill (+0.2%)"}})
