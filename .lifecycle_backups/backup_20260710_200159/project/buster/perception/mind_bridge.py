from __future__ import annotations

from typing import Any, Dict

try:
    from buster.mind import MindEngine
except Exception:  # pragma: no cover
    MindEngine = None  # type: ignore


class PerceptionMindBridge:
    """Routes eyes/ears/screen/device observations into the Mind layer."""

    def __init__(self, mind: Any | None = None):
        self.mind = mind or (MindEngine() if MindEngine else None)

    def submit_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        if self.mind is None:
            return {"accepted": False, "reason": "MindEngine unavailable", "observation": observation}
        return self.mind.perceive(
            source=observation.get("source", "perception"),
            kind=observation.get("kind", "observation"),
            title=observation.get("title", "Observation"),
            details=observation.get("details", ""),
            importance=float(observation.get("importance", 0.5)),
            urgency=float(observation.get("urgency", 0.5)),
            confidence=float(observation.get("confidence", 0.5)),
        )
