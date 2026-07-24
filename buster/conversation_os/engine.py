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