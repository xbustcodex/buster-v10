from __future__ import annotations

from typing import Any, Dict, List

from buster.mind import MindEngine


class MindCompanionBridge:
    """Turns cognitive state into meaningful companion messages."""

    def __init__(self, mind: MindEngine | None = None):
        self.mind = mind or MindEngine()

    def suggestions(self) -> List[str]:
        state = self.mind.think()
        messages: List[str] = []
        focus = state.get("attention", {}).get("current_focus")
        if focus and focus.get("priority", 0) >= 0.75:
            messages.append(f"I noticed {focus.get('title')}. Priority is {focus.get('priority')}. I can help with that.")
        for item in state.get("curiosity_suggestions", [])[:2]:
            messages.append(item.get("title", "I found a useful improvement opportunity."))
        return messages
