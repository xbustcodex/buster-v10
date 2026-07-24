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