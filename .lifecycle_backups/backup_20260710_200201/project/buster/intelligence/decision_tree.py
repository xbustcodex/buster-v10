from __future__ import annotations

from typing import Any, Dict


class DecisionTree:
    def decide(self, confidence: Dict[str, Any], risk: Dict[str, Any]) -> str:
        if risk.get("level") == "blocked":
            return "blocked"
        if confidence.get("should_ask_user"):
            return "ask_user"
        if confidence.get("score", 0) >= 0.85 and risk.get("level") == "low":
            return "auto_execute"
        if confidence.get("score", 0) >= 0.60:
            return "prepare_plan"
        return "ask_user"
