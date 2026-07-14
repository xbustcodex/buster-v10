from __future__ import annotations
from typing import Dict, Any
from .learner import VisualLearner

class VisualLearningEngine:
    def __init__(self, data_dir: str = "data") -> None: self.learner = VisualLearner(data_dir)
    def record_camera_observation(self, label: str, confidence: float = 0.0, context: str = "", details: Dict[str, Any] | None = None) -> Dict[str, Any]: return self.learner.observe(label=label, confidence=confidence, context=context, source="camera", details=details or {})
    def learn_from_recent_camera(self) -> Dict[str, Any]:
        patterns = self.learner.learn_patterns(); return {"patterns_found": len(patterns), "patterns": patterns, "summary": self.learner.summarize()}
