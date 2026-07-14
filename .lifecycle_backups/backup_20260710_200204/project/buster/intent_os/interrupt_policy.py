from __future__ import annotations

from enum import Enum
from typing import Dict

from .intent_model import IntentHypothesis


class InterruptMode(str, Enum):
    SILENT = "silent"
    ASSISTANT = "assistant"
    COMPANION = "companion"
    PARTNER = "partner"


class InterruptPolicy:
    def __init__(self, mode: InterruptMode | str = InterruptMode.COMPANION) -> None:
        self.mode = InterruptMode(mode)

    def should_speak(self, hypothesis: IntentHypothesis) -> bool:
        if self.mode == InterruptMode.SILENT:
            return hypothesis.confidence >= 0.98 and hypothesis.risk != "low"
        if self.mode == InterruptMode.ASSISTANT:
            return hypothesis.confidence >= 0.9
        if self.mode == InterruptMode.COMPANION:
            return hypothesis.confidence >= 0.8
        if self.mode == InterruptMode.PARTNER:
            return hypothesis.confidence >= 0.6
        return False

    def style(self) -> Dict[str, str]:
        return {
            "mode": self.mode.value,
            "description": {
                InterruptMode.SILENT: "Only critical interruptions.",
                InterruptMode.ASSISTANT: "Brief useful updates.",
                InterruptMode.COMPANION: "Natural proactive updates.",
                InterruptMode.PARTNER: "Active collaboration and narration.",
            }[self.mode],
        }
