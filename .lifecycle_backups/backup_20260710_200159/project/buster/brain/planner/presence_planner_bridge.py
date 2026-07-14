from __future__ import annotations
from typing import Dict, Any
try:
    from buster.presence import PresenceEngine
except Exception:
    PresenceEngine = None
class PresencePlannerBridge:
    def __init__(self, data_dir: str = "data") -> None: self.engine = PresenceEngine(data_dir) if PresenceEngine else None
    def announce_plan(self, plan_name: str, confidence: float = 0.0, risk: str = "low") -> Dict[str, Any]:
        message = f"I created the plan: {plan_name}. Confidence {round(confidence * 100)} percent. Risk {risk}."
        if not self.engine: return {"ok": False, "message": message}
        return {"ok": True, "speech": self.engine.director.request_speech(message, category="mission", reason="planner announcement")}
