from __future__ import annotations
from typing import Dict, Any, Optional
from .modes import PresencePriority
from .director import ConversationDirector

class AmbientAwareness:
    IMPORTANT_EVENTS = {
        "build_completed": (PresencePriority.IMPORTANT, "Build completed successfully."),
        "tests_failed": (PresencePriority.IMPORTANT, "The tester found an issue. I'm asking the Fixer Agent to investigate."),
        "mission_complete": (PresencePriority.IMPORTANT, "Mission complete. I recorded what worked."),
        "repository_changed": (PresencePriority.NORMAL, "Your repository changed. I can re-index it in the background."),
        "plugin_update": (PresencePriority.NORMAL, "A plugin update is available."),
        "visual_pattern_learned": (PresencePriority.NORMAL, "I learned something new from the camera."),
    }
    def __init__(self, director: ConversationDirector | None = None) -> None: self.director = director or ConversationDirector()
    def handle_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}; priority, default_message = self.IMPORTANT_EVENTS.get(event_type, (PresencePriority.LOW, "I noticed an update."))
        return self.director.request_speech(payload.get("message") or default_message, priority, payload.get("category", "mission"), reason=event_type)
