from __future__ import annotations

from typing import Dict, List

from .skill import Skill


class SkillRegistry:
    def __init__(self) -> None:
        self.skills: Dict[str, Skill] = {}

    def register(self, name: str, domain: str, description: str = "") -> Skill:
        if name not in self.skills:
            self.skills[name] = Skill(name=name, domain=domain, description=description)
        return self.skills[name]

    def get(self, name: str) -> Skill | None:
        return self.skills.get(name)

    def require(self, name: str) -> Skill:
        if name not in self.skills:
            raise KeyError(f"Missing skill: {name}")
        return self.skills[name]

    def install_defaults(self) -> None:
        self.register("python_build", "development", "Build and run Python projects")
        self.register("android_build", "development", "Build Android projects")
        self.register("esp32_workflow", "hardware", "Work with ESP32 and Arduino projects")
        self.register("pytest_debugging", "testing", "Run and debug pytest suites")
        self.register("mission_planning", "planning", "Plan autonomous missions")
        self.register("companion_dialogue", "companion", "Explain work naturally")

    def list(self) -> List[dict]:
        return [skill.to_dict() for skill in self.skills.values()]
