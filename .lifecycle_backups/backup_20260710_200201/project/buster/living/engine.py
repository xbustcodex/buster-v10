from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

from .state import LivingState, LivingMood
from .timeline import ActivityTimeline
from .notifications import NotificationCenter
from .face_controller import FaceController
from .voice_vision_bridge import VoiceVisionBridge


class LivingOSEngine:
    """
    Coordinates Buster's living UI state:
    planner decisions, agent activity, voice/vision signals,
    confidence/risk, mission timeline, and face expression.
    """

    def __init__(self, state_path: str | Path = "data/living_os_state.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.timeline = ActivityTimeline()
        self.notifications = NotificationCenter()
        self.face = FaceController()
        self.bridge = VoiceVisionBridge()
        self.state = self._load_state()

    def _load_state(self) -> LivingState:
        if self.state_path.exists():
            try:
                return LivingState.from_dict(json.loads(self.state_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        state = LivingState()
        self._save_state(state)
        return state

    def _save_state(self, state: LivingState | None = None) -> Dict[str, Any]:
        state = state or self.state
        data = state.to_dict()
        data["face"] = self.face.face_state(state.mood, state.confidence, state.risk)
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def set_mission(self, mission: str, confidence: float = 0.0, risk: str = "unknown", reason: str = "") -> Dict[str, Any]:
        mood = LivingMood.CONFIDENT if confidence >= 0.85 else LivingMood.THINKING
        self.state.update(
            current_mission=mission,
            confidence=confidence,
            risk=risk,
            mood=mood,
            last_decision=mission,
            last_reason=reason,
        )
        event = self.timeline.add("Planner", f"created mission: {mission}", confidence=confidence, risk=risk, reason=reason)
        self.state.recent_activity.append(event)
        self.notifications.notify_decision(
            "Mission created",
            mission,
            reason=reason,
            confidence=confidence,
            risk=risk,
            action="mission_created",
        )
        return self._save_state()

    def agent_update(self, agent: str, message: str, level: str = "info", confidence: float | None = None, risk: str | None = None) -> Dict[str, Any]:
        if confidence is not None:
            self.state.confidence = confidence
        if risk is not None:
            self.state.risk = risk
        self.state.update(active_agent=agent, mood=LivingMood.WORKING)
        event = self.timeline.add(agent, message, level=level, confidence=self.state.confidence, risk=self.state.risk)
        self.state.recent_activity.append(event)
        return self._save_state()

    def success(self, message: str = "Task completed") -> Dict[str, Any]:
        self.state.update(mood=LivingMood.SUCCESS, active_agent="none", confidence=max(self.state.confidence, 0.9), risk="low")
        event = self.timeline.add("Verifier", message, level="success", confidence=self.state.confidence, risk=self.state.risk)
        self.state.recent_activity.append(event)
        self.notifications.notify_decision("Task complete", message, reason="Verifier approved the result.", confidence=self.state.confidence, risk=self.state.risk)
        return self._save_state()

    def error(self, message: str, reason: str = "") -> Dict[str, Any]:
        self.state.update(mood=LivingMood.ERROR, risk="high", last_reason=reason)
        event = self.timeline.add("System", message, level="error", reason=reason)
        self.state.recent_activity.append(event)
        self.notifications.notify_decision("Needs attention", message, reason=reason, confidence=self.state.confidence, risk="high")
        return self._save_state()

    def voice_heard(self, text: str) -> Dict[str, Any]:
        signal = self.bridge.voice_signal(text=text, listening=True)
        self.state.update(listening=True, mood=signal["mood"])
        event = self.timeline.add("Voice", f"heard: {text}")
        self.state.recent_activity.append(event)
        self.state.signals["voice"] = signal
        return self._save_state()

    def vision_seen(self, summary: str) -> Dict[str, Any]:
        signal = self.bridge.vision_signal(summary=summary, watching=True)
        self.state.update(watching=True, mood=signal["mood"])
        event = self.timeline.add("Vision", f"observed: {summary}")
        self.state.recent_activity.append(event)
        self.state.signals["vision"] = signal
        return self._save_state()

    def standby(self) -> Dict[str, Any]:
        self.state.update(mood=LivingMood.STANDBY, listening=False, watching=False, active_agent="none")
        event = self.timeline.add("System", "returned to standby")
        self.state.recent_activity.append(event)
        return self._save_state()

    def status(self) -> Dict[str, Any]:
        data = self._save_state()
        data["timeline"] = self.timeline.list_recent(15)
        data["notifications"] = self.notifications.recent(5)
        return data
