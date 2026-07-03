from __future__ import annotations
from typing import Any, Dict
try:
    from buster.experience.engine import ExperienceEngine
except Exception:
    ExperienceEngine = None  # type: ignore

class ExperienceAdvisor:
    """Feeds Experience Engine recommendations into the Intelligence Core."""
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir
        self.engine = ExperienceEngine(data_dir) if ExperienceEngine else None
    def advise(self, project_type: str, task: str = "") -> Dict[str, Any]:
        if not self.engine:
            return {"project_type": project_type, "task": task, "recommended_strategy": "default", "confidence": 0.5, "reason": "Experience Engine unavailable"}
        rec = self.engine.recommend_for_project(project_type, task)
        rec["reason"] = "Based on previous Buster engineering outcomes."
        return rec
