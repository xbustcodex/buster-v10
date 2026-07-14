from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
from .records import ExperienceRecord
from .storage import load_json, save_json

class ProjectExperienceIndex:
    """Indexes experience by project and project type."""
    def __init__(self, path: str | Path = "data/project_experience_index.json") -> None:
        self.path = Path(path)
        data = load_json(self.path, {"projects": {}, "types": {}})
        self.data = data if isinstance(data, dict) else {"projects": {}, "types": {}}
        self.data.setdefault("projects", {}); self.data.setdefault("types", {})
    def add(self, record: ExperienceRecord) -> None:
        for section, key in (("projects", record.project), ("types", record.project_type)):
            bucket = self.data[section].setdefault(key or "default", {"total": 0, "successes": 0, "failures": 0, "strategies": {}, "last_seen": ""})
            bucket["total"] += 1
            if record.success: bucket["successes"] += 1
            else: bucket["failures"] += 1
            bucket["last_seen"] = record.timestamp
            strat = bucket["strategies"].setdefault(record.strategy, {"successes": 0, "failures": 0})
            if record.success: strat["successes"] += 1
            else: strat["failures"] += 1
        self.save()
    def summary_for_type(self, project_type: str) -> Dict[str, Any]:
        return self.data.get("types", {}).get(project_type or "general", {})
    def best_strategy(self, project_type: str) -> str:
        summary = self.summary_for_type(project_type)
        strategies = summary.get("strategies", {}) if isinstance(summary, dict) else {}
        best, best_score = "default", -1.0
        for name, stats in strategies.items():
            total = max(1, stats.get("successes", 0) + stats.get("failures", 0))
            score = stats.get("successes", 0) / total
            if score > best_score: best, best_score = name, score
        return best
    def save(self) -> None:
        save_json(self.path, self.data)
