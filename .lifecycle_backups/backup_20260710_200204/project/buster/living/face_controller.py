from __future__ import annotations

from typing import Dict


class FaceController:
    """Converts Buster state into simple face expressions for the UI."""

    EXPRESSIONS: Dict[str, str] = {
        "standby": "neutral",
        "thinking": "focused",
        "working": "active",
        "watching": "alert",
        "listening": "listening",
        "confident": "happy",
        "cautious": "concerned",
        "error": "worried",
        "success": "proud",
    }

    def expression_for_mood(self, mood: str) -> str:
        return self.EXPRESSIONS.get(mood, "neutral")

    def expression_for_signal(self, confidence: float, risk: str = "unknown", has_error: bool = False) -> str:
        if has_error:
            return "worried"
        if risk.lower() in {"high", "critical"}:
            return "concerned"
        if confidence >= 0.85:
            return "happy"
        if confidence >= 0.55:
            return "focused"
        return "thinking"

    def face_state(self, mood: str, confidence: float = 0.0, risk: str = "unknown", has_error: bool = False) -> Dict[str, str]:
        expression = (
            self.expression_for_signal(confidence, risk, has_error)
            if confidence
            else self.expression_for_mood(mood)
        )
        return {"mood": mood, "expression": expression}
