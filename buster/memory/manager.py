# buster/memory/manager.py
import json
from pathlib import Path
from typing import Dict, Any, List

class CompartmentalizedMemory:
    """Manages 6 explicit system contexts to optimize historical lookups and strategy recalls."""
    
    def __init__(self, base_dir: str = "buster/memory"):
        self.base_dir = Path(base_dir)
        self.categories = [
            "user_memory",       # Preferences, coding styles, custom choices[cite: 9]
            "project_memory",    # Framework selections (PySide6, dependencies)[cite: 9]
            "skill_memory",      # Documented module knowledge blocks[cite: 9]
            "experience_memory", # Action transaction logs and runtime histories[cite: 9]
            "failure_memory",    # Failed attempts, syntax issues, breaking crashes[cite: 9]
            "strategy_memory"    # Reusable correction blueprints matched from failures[cite: 9]
        ]
        self._initialize_tree()

    def _initialize_tree(self):
        for cat in self.categories:
            (self.base_dir / cat).mkdir(parents=True, exist_ok=True)

    def write_record(self, category: str, key_id: str, payload: Dict[str, Any]):
        if category not in self.categories:
            raise ValueError(f"Invalid memory category context: {category}")
            
        target_path = self.base_dir / category / f"{key_id}.json"
        target_path.write_text(json.dumps(payload, indent=4, default=str), encoding="utf-8")

    def read_record(self, category: str, key_id: str) -> Dict[str, Any]:
        target_path = self.base_dir / category / f"{key_id}.json"
        if not target_path.exists():
            return {}
        try:
            return json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def log_failure_incident(self, incident_id: str, failed_action: str, runtime_error: str, lesson_learned: str):
        """Strict implementation writing directly into failure_memory and strategy_memory blocks."""
        failure_payload = {
            "attempt": failed_action,
            "result": "failed",
            "error_dump": runtime_error,
            "lesson": lesson_learned
        }
        self.write_record("failure_memory", incident_id, failure_payload)

        strategy_payload = {
            "trigger_issue": runtime_error,
            "recommended_blueprint": lesson_learned,
            "success_rate_projection": 95.0
        }
        self.write_record("strategy_memory", f"strategy_{incident_id}", strategy_payload)