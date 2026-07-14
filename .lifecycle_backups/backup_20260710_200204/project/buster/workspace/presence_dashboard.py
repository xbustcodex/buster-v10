from __future__ import annotations
from typing import Dict, Any
try:
    from buster.visual_learning import VisualLearningEngine
except Exception:
    VisualLearningEngine = None

class PresenceDashboard:
    def __init__(self, data_dir: str = "data") -> None: self.visual = VisualLearningEngine(data_dir) if VisualLearningEngine else None
    def snapshot(self) -> Dict[str, Any]:
        visual_summary = self.visual.learner.summarize() if self.visual else {}
        return {"title": "Buster Presence", "mode": "companion", "status": "alive", "visual_learning": visual_summary, "capabilities": ["talk_first", "ambient_awareness", "context_awareness", "camera_learning"]}
