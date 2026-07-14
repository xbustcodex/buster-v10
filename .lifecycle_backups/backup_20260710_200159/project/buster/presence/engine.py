from __future__ import annotations
from typing import Dict, Any, Optional
from .director import ConversationDirector
from .ambient_awareness import AmbientAwareness
from .context_awareness import ContextAwareness
from .modes import state_for_activity

class PresenceEngine:
    def __init__(self, data_dir: str = "data") -> None:
        self.director = ConversationDirector(data_dir=data_dir); self.ambient = AmbientAwareness(self.director); self.context = ContextAwareness()
    def set_companion_mode(self) -> Dict[str, Any]: return self.director.set_mode("companion")
    def on_activity(self, activity: str, message: str | None = None) -> Dict[str, Any]:
        emotion = state_for_activity(activity); speech = self.director.request_speech(message, category="mission", reason=activity) if message else None
        return {"activity": activity, "emotion": emotion, "speech": speech}
    def on_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: return self.ambient.handle_event(event_type, payload)
    def inspect_context(self, active_window: str = "", device_hint: str = "", idle_minutes: int = 0) -> Dict[str, Any]:
        ctx = self.context.describe_context(active_window, device_hint, idle_minutes)
        for suggestion in ctx.get("suggestions", [])[:1]: self.director.request_speech(suggestion, category="context", reason="context awareness")
        return ctx
