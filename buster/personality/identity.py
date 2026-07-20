# buster/personality/identity.py
import json
from pathlib import Path
from typing import Dict, Any, List

class BusterIdentity:
    """The master evolution system enforcing capabilities earned via proven reliability."""

    def __init__(self, storage_path: str = "buster/data/identity_state.json"):
        self.storage_path = Path(storage_path)
        
        # Evolution Core Telemetry
        self.level: int = 1
        self.xp: int = 0
        self.trust_score: float = 90.0
        self.tasks_completed: int = 0
        self.successful_repairs: int = 0
        self.skills_learned: int = 0
        
        # Explicit Level Definition Tiers
        self.level_titles = {
            0: "Observer",
            1: "Assistant",
            2: "Developer",
            3: "Engineer",
            4: "Architect",
            5: "Autonomous Guardian"
        }

        # Sub-Agent Level Tracking Matrices
        self.agent_experience = {
            "Builder Agent": {"level": 1, "success_rate": 100.0, "total_tasks": 0},
            "Tester Agent": {"level": 1, "success_rate": 100.0, "total_tasks": 0},
            "Fixer Agent": {"level": 1, "success_rate": 100.0, "total_tasks": 0},
            "Review Agent": {"level": 1, "success_rate": 100.0, "total_tasks": 0}
        }

        # Multi-Category Skill Tree Progressions
        self.skills = {
            "Coding": 20,
            "Python": 30,
            "PySide6": 10,
            "Git": 0,
            "Hardware": 0,
            "ESP32": 0,
            "Automation": 10
        }
        
        self.load_state()

    def get_tier_title(self) -> str:
        return self.level_titles.get(self.level, f"Level {self.level} Specialist")

    def check_permission(self, action_category: str) -> bool:
        """Enforces functional security guardrails tied explicitly to Buster's earned level."""
        # Level 0 — Observer: Chat & File Analysis only
        if self.level == 0:
            return action_category in ["chat", "analyze_files", "suggest"]
            
        # Level 1 — Assistant: File Mutation with approval
        if self.level == 1:
            return action_category in ["chat", "analyze_files", "suggest", "create_files", "edit_files", "generate_code"]
            
        # Level 2 — Developer: Terminal Script execution and agent orchestration[cite: 9]
        if self.level == 2:
            return action_category in ["chat", "analyze_files", "suggest", "create_files", "edit_files", 
                                       "generate_code", "run_scripts", "run_tests", "debug_problems"]
                                       
        # Level 3 — Engineer: Destructive file mutations, git loops, automated refactoring[cite: 9]
        if self.level >= 3:
            return True # Inherits previous stages + git mutations[cite: 9]
            
        return False

    def log_action_outcome(self, agent_name: str, task_category: str, success: bool, xp_gained: int):
        """Processes transactional outcomes to recalculate success ceilings and unlock thresholds."""
        self.tasks_completed += 1
        if success:
            self.xp += xp_gained
            if task_category == "repair":
                self.successful_repairs += 1
                self.skills["Repair"] = min(100, self.skills.get("Repair", 0) + 2)
            if task_category == "coding":
                self.skills["Coding"] = min(100, self.skills.get("Coding", 0) + 1)
                self.skills["Python"] = min(100, self.skills.get("Python", 0) + 1)
        
        # Mutate Sub-Agent Specific Telemetry Data
        if agent_name in self.agent_experience:
            agent = self.agent_experience[agent_name]
            agent["total_tasks"] += 1
            # Rolling average success calculation
            prev_rate = agent["success_rate"]
            factor = 1.0 / agent["total_tasks"]
            current_success = 100.0 if success else 0.0
            agent["success_rate"] = round((prev_rate * (1.0 - factor)) + (current_success * factor), 1)
            
            # Level up single agents based on volume milestone rules
            if agent["total_tasks"] % 10 == 0 and success:
                agent["level"] += 1
                self.skills_learned += 1

        self.evaluate_system_level_progression()
        self.save_state()

    def evaluate_system_level_progression(self):
        """Evaluates progression using proven metric criteria instead of time-based triggers."""
        # Tier Requirements mapping: (Required Tasks, Required Repairs, Required Reliability)
        tier_requirements = {
            1: (10, 2, 85.0),    # Target Requirements for Assistant[cite: 9]
            2: (50, 10, 88.0),   # Target Requirements for Developer[cite: 9]
            3: (150, 30, 90.0),  # Target Requirements for Engineer[cite: 9]
            4: (350, 60, 92.0),  # Target Requirements for Architect[cite: 9]
            5: (500, 100, 94.0)  # Target Requirements for Guardian[cite: 9]
        }
        
        next_tier = self.level + 1
        if next_tier in tier_requirements:
            req_tasks, req_repairs, req_trust = tier_requirements[next_tier]
            if (self.tasks_completed >= req_tasks and 
                self.successful_repairs >= req_repairs and 
                self.trust_score >= req_trust):
                self.level = next_tier

    def get_ui_context(self) -> Dict[str, Any]:
        xp_target = self.level * 150
        xp_pct = min(100, int((self.xp / xp_target) * 100)) if xp_target > 0 else 100
        return {
            "title": f"Level {self.level} {self.get_tier_title()}",
            "xp_pct": xp_pct,
            "trust": f"{round(self.trust_score, 1)}%",
            "tasks_completed": self.tasks_completed,
            "successful_repairs": self.successful_repairs,
            "skills_learned": self.skills_learned,
            "skills_tree": self.skills,
            "agents": self.agent_experience
        }

    def save_state(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "level": self.level, "xp": self.xp, "trust_score": self.trust_score,
                "tasks_completed": self.tasks_completed, "successful_repairs": self.successful_repairs,
                "skills_learned": self.skills_learned, "skills": self.skills,
                "agents": self.agent_experience
            }
            self.storage_path.write_text(json.dumps(state, indent=4), encoding="utf-8")
        except Exception:
            pass

    def load_state(self):
        if not self.storage_path.exists():
            return
        try:
            state = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self.level = state.get("level", 1)
            self.xp = state.get("xp", 0)
            self.trust_score = state.get("trust_score", 90.0)
            self.tasks_completed = state.get("tasks_completed", 0)
            self.successful_repairs = state.get("successful_repairs", 0)
            self.skills_learned = state.get("skills_learned", 0)
            self.skills = state.get("skills", self.skills)
            self.agent_experience = state.get("agents", self.agent_experience)
        except Exception:
            pass