from __future__ import annotations

from typing import Any, Dict

from buster.living.engine import LivingOSEngine


class MissionActivityRecorder:
    """
    Convenience recorder for Mission Control timeline entries:
    Planner, Repository, Builder, Tester, Fixer, Verifier,
    Learning Engine, and Experience.
    """

    def __init__(self):
        self.engine = LivingOSEngine()

    def planner_created_mission(self, mission: str, confidence: float = 0.9, risk: str = "low") -> Dict[str, Any]:
        return self.engine.set_mission(mission, confidence=confidence, risk=risk, reason="Planner selected best available strategy.")

    def repository_indexed(self, project: str) -> Dict[str, Any]:
        return self.engine.agent_update("Repository", f"indexed project: {project}")

    def builder_generated_code(self, target: str) -> Dict[str, Any]:
        return self.engine.agent_update("Builder", f"generated code: {target}")

    def tester_found_failure(self, count: int = 1) -> Dict[str, Any]:
        word = "failure" if count == 1 else "failures"
        return self.engine.agent_update("Tester", f"found {count} {word}", level="warning", risk="medium")

    def fixer_repaired_issue(self, issue: str = "issue") -> Dict[str, Any]:
        return self.engine.agent_update("Fixer", f"repaired {issue}", confidence=0.82, risk="low")

    def verifier_approved_build(self) -> Dict[str, Any]:
        return self.engine.success("approved build")

    def learning_recorded_pattern(self, pattern: str) -> Dict[str, Any]:
        return self.engine.agent_update("Learning Engine", f"recorded new pattern: {pattern}", confidence=0.9)

    def experience_updated_skill(self, skill: str, delta: float) -> Dict[str, Any]:
        sign = "+" if delta >= 0 else ""
        return self.engine.agent_update("Experience", f"updated {skill} skill ({sign}{delta:.1f}%)", confidence=0.9)
