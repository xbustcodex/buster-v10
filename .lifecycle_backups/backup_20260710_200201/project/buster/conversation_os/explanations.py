from __future__ import annotations

from typing import Dict, Any


class DecisionExplainer:
    def explain(self, decision: Dict[str, Any]) -> str:
        action = decision.get("action") or decision.get("event") or "decision"
        confidence = decision.get("confidence")
        risk = decision.get("risk")
        reason = decision.get("reason") or decision.get("why") or "based on the current mission context"
        parts = [f"I chose {action}"]
        if confidence is not None:
            try:
                parts.append(f"with {float(confidence) * 100:.0f}% confidence")
            except Exception:
                parts.append(f"with confidence {confidence}")
        if risk:
            parts.append(f"and {risk} risk")
        parts.append(f"because {reason}.")
        return " ".join(parts)

    def explain_event(self, event: Dict[str, Any]) -> str:
        actor = event.get("actor") or event.get("source") or "Buster"
        title = event.get("title") or event.get("event") or event.get("type") or "updated the mission"
        message = event.get("message") or event.get("description") or ""
        if message:
            return f"{actor}: {title}. {message}"
        return f"{actor}: {title}."
