from __future__ import annotations

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
