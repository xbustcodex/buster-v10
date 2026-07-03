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
