from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

from .registry import SkillRegistry


class SkillGrowthEngine:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.registry = SkillRegistry()
        self.registry.install_defaults()
        self.state_file = self.data_dir / "skill_growth_state.json"

    def record(self, skill_name: str, success: bool = True, weight: float = 0.02) -> Dict[str, Any]:
        skill = self.registry.require(skill_name)
        skill.record_result(success, weight)
        self._persist()
        return skill.to_dict()

    def infer_skill_from_event(self, event: Dict[str, Any]) -> str:
        text = (str(event.get("type", "")) + " " + str(event.get("summary", "")) + " " + str(event.get("capability", ""))).lower()
        if "android" in text:
            return "android_build"
        if "esp32" in text or "arduino" in text:
            return "esp32_workflow"
        if "pytest" in text or "test" in text:
            return "pytest_debugging"
        if "mission" in text or "plan" in text:
            return "mission_planning"
        if "speak" in text or "companion" in text:
            return "companion_dialogue"
        return "python_build"

    def record_event(self, event: Dict[str, Any], success: bool = True) -> Dict[str, Any]:
        return self.record(self.infer_skill_from_event(event), success=success)

    def status(self) -> Dict[str, Any]:
        return {"skills": self.registry.list()}

    def _persist(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.status(), indent=2), encoding="utf-8")
