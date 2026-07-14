from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List
from .storage import load_json, save_json

@dataclass
class SkillProfile:
    name: str
    level: int = 1
    confidence: float = 0.50
    successes: int = 0
    failures: int = 0
    last_used: str = ""
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillProfile":
        return cls(name=data.get("name", "general"), level=int(data.get("level", 1)), confidence=float(data.get("confidence", 0.50)), successes=int(data.get("successes", 0)), failures=int(data.get("failures", 0)), last_used=data.get("last_used", ""))

class SkillEngine:
    """Tracks Buster's skill growth by project type and tool domain."""
    def __init__(self, path: str | Path = "data/skill_profiles.json") -> None:
        self.path = Path(path)
        raw = load_json(self.path, {})
        self.skills: Dict[str, SkillProfile] = {name: SkillProfile.from_dict(value) for name, value in raw.items()} if isinstance(raw, dict) else {}
    def get(self, name: str) -> SkillProfile:
        key = (name or "general").lower().strip()
        if key not in self.skills:
            self.skills[key] = SkillProfile(name=key)
            self.save()
        return self.skills[key]
    def update(self, name: str, success: bool, timestamp: str = "") -> SkillProfile:
        skill = self.get(name)
        if success: skill.successes += 1
        else: skill.failures += 1
        total = max(1, skill.successes + skill.failures)
        skill.confidence = round(0.35 + 0.65 * (skill.successes / total), 3)
        skill.level = max(1, min(5, 1 + (skill.successes // 3)))
        skill.last_used = timestamp or skill.last_used
        self.save()
        return skill
    def top_skills(self, limit: int = 5) -> List[SkillProfile]:
        return sorted(self.skills.values(), key=lambda s: (s.level, s.confidence, s.successes), reverse=True)[:limit]
    def save(self) -> None:
        save_json(self.path, {name: profile.to_dict() for name, profile in self.skills.items()})
