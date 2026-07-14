from __future__ import annotations
from typing import Dict, Any
class PresenceWidgetModel:
    def __init__(self) -> None: self.mode = "companion"; self.emotion = "relaxed"; self.last_message = "Buster is present."
    def update(self, mode: str | None = None, emotion: str | None = None, message: str | None = None) -> Dict[str, Any]:
        if mode: self.mode = mode
        if emotion: self.emotion = emotion
        if message: self.last_message = message
        return self.to_dict()
    def to_dict(self) -> Dict[str, Any]: return {"mode": self.mode, "emotion": self.emotion, "last_message": self.last_message}
