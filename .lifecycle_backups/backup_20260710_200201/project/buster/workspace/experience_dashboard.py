from __future__ import annotations
from typing import Any, Dict
try:
    from buster.experience.engine import ExperienceEngine
except Exception:
    ExperienceEngine = None  # type: ignore

class ExperienceDashboard:
    """Backend model for showing experience stats in Mission Control."""
    def __init__(self, data_dir: str = "data") -> None:
        self.engine = ExperienceEngine(data_dir) if ExperienceEngine else None
    def snapshot(self) -> Dict[str, Any]:
        if not self.engine:
            return {"available": False, "records": 0, "top_skills": []}
        data = self.engine.summary()
        data["available"] = True
        data["title"] = "Experience Engine"
        return data
