from __future__ import annotations
from typing import Dict, Any
try:
    from buster.visual_learning import VisualLearningEngine
except Exception:
    VisualLearningEngine = None

class VisionLearningBridge:
    def __init__(self, data_dir: str = "data") -> None: self.engine = VisualLearningEngine(data_dir) if VisualLearningEngine else None
    def record_detection(self, label: str, confidence: float = 0.0, context: str = "", details: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self.engine: return {"ok": False, "reason": "VisualLearningEngine unavailable"}
        return {"ok": True, "observation": self.engine.record_camera_observation(label, confidence, context, details or {})}
    def learn(self) -> Dict[str, Any]:
        if not self.engine: return {"ok": False, "reason": "VisualLearningEngine unavailable"}
        result = self.engine.learn_from_recent_camera(); result["ok"] = True; return result
