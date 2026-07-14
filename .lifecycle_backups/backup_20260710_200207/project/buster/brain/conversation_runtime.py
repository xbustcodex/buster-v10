from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from buster.brain.unified_agent_loop import UnifiedAgentLoop


@dataclass
class ConversationTurn:
    role: str
    text: str


class UnifiedConversationRuntime:
    """
    Shared conversation runtime for UI, typed commands, and voice.

    Keeps recent context and sends all user input through the same
    UnifiedAgentLoop.
    """

    def __init__(self, ai_provider, max_turns: int = 8):
        self.loop = UnifiedAgentLoop(ai_provider)
        self.max_turns = max_turns
        self.history: List[ConversationTurn] = []

    def _context(self) -> str:
        recent = self.history[-self.max_turns:]
        return "\n".join(f"{turn.role}: {turn.text}" for turn in recent)

    def ask(self, text: str, *, voice: bool = False) -> str:
        self.history.append(ConversationTurn("user", text))
        reply = self.loop.run(text, voice=voice)
        self.history.append(ConversationTurn("buster", reply))
        self.history = self.history[-self.max_turns:]
        return reply

    def clear(self):
        self.history.clear()
        return "Conversation context cleared."
