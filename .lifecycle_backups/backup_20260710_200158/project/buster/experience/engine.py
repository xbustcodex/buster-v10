from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from .records import ExperienceRecord, make_experience_record
from .storage import load_json, save_json
from .skills import SkillEngine
from .design_decisions import DesignDecisionStore
from .project_experience import ProjectExperienceIndex
from .user_overrides import UserOverrideStore

class ExperienceEngine:
    """Coordinates Buster's engineering experience layer."""
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.memory_path = self.data_dir / "experience_memory.json"
        self.records: List[Dict[str, Any]] = load_json(self.memory_path, [])
        if not isinstance(self.records, list): self.records = []
        self.skills = SkillEngine(self.data_dir / "skill_profiles.json")
        self.decisions = DesignDecisionStore(self.data_dir / "design_decisions.json")
        self.projects = ProjectExperienceIndex(self.data_dir / "project_experience_index.json")
        self.overrides = UserOverrideStore(self.data_dir / "user_overrides.json")
    def record_outcome(self, record: ExperienceRecord | Dict[str, Any]) -> ExperienceRecord:
        if isinstance(record, dict): record = ExperienceRecord.from_dict(record)
        self.records.append(record.to_dict())
        save_json(self.memory_path, self.records)
        self.skills.update(record.project_type, record.success, record.timestamp)
        self.projects.add(record)
        for choice in record.design_choices:
            self.decisions.record(record.project_type, choice, record.outcome, record.confidence)
        return record
    def record_simple(self, project: str, project_type: str, task: str, strategy: str, outcome: str, **kwargs: Any) -> ExperienceRecord:
        return self.record_outcome(make_experience_record(project, project_type, task, strategy, outcome, **kwargs))
    def recommend_for_project(self, project_type: str, task: str = "") -> Dict[str, Any]:
        skill = self.skills.get(project_type)
        best_strategy = self.projects.best_strategy(project_type)
        designs = self.decisions.recommend(project_type)
        confidence = min(0.99, max(0.35, skill.confidence + (0.05 if best_strategy != "default" else 0.0)))
        return {"project_type": project_type or "general", "task": task, "recommended_strategy": best_strategy, "confidence": round(confidence, 3), "skill": skill.to_dict(), "recommended_designs": designs, "recent_overrides": self.overrides.recent(5)}
    def summary(self) -> Dict[str, Any]:
        successes = sum(1 for r in self.records if str(r.get("outcome", "")).lower() in {"success", "passed", "fixed", "accepted", "completed"})
        total = len(self.records)
        return {"records": total, "successes": successes, "failures": total - successes, "success_rate": round(successes / total, 3) if total else 0.0, "top_skills": [s.to_dict() for s in self.skills.top_skills(5)]}
