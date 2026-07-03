from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ConfidenceResult:
    score: float
    level: str
    reason: str
    should_ask_user: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "reason": self.reason,
            "should_ask_user": self.should_ask_user,
        }


class ConfidenceEngine:
    def score(self, signals: Dict[str, Any] | None = None) -> ConfidenceResult:
        signals = signals or {}
        value = 0.65

        if signals.get("tests_passed"):
            value += 0.15
        if signals.get("known_strategy"):
            value += 0.10
        if signals.get("similar_success"):
            value += 0.10
        if signals.get("has_plugin"):
            value += 0.05

        if signals.get("tests_failed"):
            value -= 0.20
        if signals.get("destructive_action"):
            value -= 0.25
        if signals.get("unknown_project"):
            value -= 0.15
        if signals.get("high_risk"):
            value -= 0.20

        value = max(0.0, min(1.0, value))

        if value >= 0.85:
            level = "high"
            reason = "Strong signals found; safe to proceed."
            ask = False
        elif value >= 0.60:
            level = "medium"
            reason = "Enough confidence to prepare a plan, but verify before risky action."
            ask = bool(signals.get("destructive_action") or signals.get("high_risk"))
        else:
            level = "low"
            reason = "Not enough confidence; user confirmation recommended."
            ask = True

        return ConfidenceResult(round(value, 2), level, reason, ask)
