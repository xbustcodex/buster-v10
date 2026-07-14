from __future__ import annotations
from typing import Any, Dict
try:
    from buster.intelligence.experience_advisor import ExperienceAdvisor
except Exception:
    ExperienceAdvisor = None  # type: ignore

class ExperiencePlanner:
    """Creates safer execution hints using past project experience."""
    def __init__(self, data_dir: str = "data") -> None:
        self.advisor = ExperienceAdvisor(data_dir) if ExperienceAdvisor else None
    def plan_with_experience(self, project_type: str, task: str) -> Dict[str, Any]:
        if not self.advisor:
            return {"steps": ["plan", "execute", "verify"], "confidence": 0.5}
        advice = self.advisor.advise(project_type, task)
        strategy = advice.get("recommended_strategy") or "default"
        steps = ["inspect_project", "select_strategy"]
        steps.append(f"apply_strategy:{strategy}" if strategy != "default" else "use_default_strategy")
        steps.extend(["run_agents", "verify_result", "record_experience"])
        return {"project_type": project_type, "task": task, "strategy": strategy, "confidence": advice.get("confidence", 0.5), "steps": steps, "advice": advice}
