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

    # --- NEW EXTENSIONS (APPENDED TO ORIGINAL CLASS) ---
    def process_evolution_xp(self, evolution_state: Any, event_bus: Any, action_type: str, success: bool) -> None:
        """Processes evaluated records directly through the experience-to-XP scaling matrices."""
        xp_gain = 0
        trust_gain = 0.0
        capability_key = "testing"  # Standardized to snake_case matching the authority keys

        # Action valuation ruleset matrices
        if action_type == "test_run":
            xp_gain = 5 if success else -2
            trust_gain = 1.0 if success else -3.0
            capability_key = "testing"
        elif action_type == "repair":
            xp_gain = 20 if success else -10
            trust_gain = 3.0 if success else -6.0
            capability_key = "file_editing"
        elif action_type == "guardrail_intercept":
            xp_gain = 25 if success else -15
            trust_gain = 5.0 if success else -12.0
            capability_key = "system_maintenance"
        elif action_type == "user_approved":
            xp_gain = 10 if success else -5
            trust_gain = 2.0 if success else -4.0
            capability_key = "git_operations"

        # Mutate the authority state records safely
        evolution_state.current_xp += xp_gain
        if evolution_state.current_xp < 0:
            evolution_state.current_xp = 0

        # Adjust trust globally
        evolution_state.trust_score = min(100.0, max(0.0, evolution_state.trust_score + trust_gain))

        # Sync capability specific trust using standardized keys
        if capability_key in evolution_state.capability_trust:
            current_cap_lvl = evolution_state.capability_trust[capability_key]
            if success and current_cap_lvl < 5:
                evolution_state.capability_trust[capability_key] += 1
            elif not success and current_cap_lvl > 0:
                evolution_state.capability_trust[capability_key] -= 1

        # Check thresholds for complete Engine Level Progression
        leveled_up = False
        if evolution_state.current_xp >= evolution_state.xp_to_next_level:
            evolution_state.current_xp -= evolution_state.xp_to_next_level
            evolution_state.level += 1
            evolution_state.xp_to_next_level = int(evolution_state.xp_to_next_level * 1.25)
            leveled_up = True

        evolution_state.save()

        # Build full unified payload mapping get_ui_context() to to_dict() seamlessly
        ui_payload = evolution_state.to_dict()

        # Direct synchronization across the Event Bus system hooks
        event_bus.publish("experience.recorded", {"action_type": action_type, "success": success, "xp_gained": xp_gain})
        
        # Publish master consolidated change notification
        event_bus.publish("evolution.changed", ui_payload)
        
        if leveled_up:
            event_bus.publish("level.progressed", ui_payload)