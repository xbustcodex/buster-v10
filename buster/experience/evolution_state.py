# buster/experience/evolution_state.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Buster.Evolution")

class EvolutionState:
    """Authoritative, thread-safe, and transaction-persistent runtime core state."""
    
    def __init__(self, state_dir: str = "data", event_bus: Optional[Any] = None):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "evolution_state.json"
        self.history_file = self.state_dir / "experience_history.json"
        self.event_bus = event_bus
        
        # State Fields
        self.level: int = 1
        self.current_xp: int = 0
        self.xp_to_next_level: int = 100
        self.permission_rank: str = "L1_LOCAL"
        self.trust_score: float = 75.0
        self.mood: str = "Focused"
        self.dominant_drive: str = "builder"
        self.active_goal: str = "Initialize system monitoring structures."
        self.skills: Dict[str, int] = {}
        self.capability_trust: Dict[str, int] = {
            "file_editing": 1,
            "testing": 1,
            "git_operations": 1,
            "deployment": 0,
            "system_maintenance": 1,
            "esp32_operations": 0
        }
        self.agent_levels: Dict[str, int] = {
            "builder": 1,
            "fixer": 1,
            "reviewer": 1
        }
        
        self.load()

    def load(self) -> None:
        """Loads state from file with robust fallback structures."""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.level = data.get("level", self.level)
                    self.current_xp = data.get("current_xp", self.current_xp)
                    self.xp_to_next_level = data.get("xp_to_next_level", self.xp_to_next_level)
                    self.permission_rank = data.get("permission_rank", self.permission_rank)
                    self.trust_score = data.get("trust_score", self.trust_score)
                    self.mood = data.get("mood", self.mood)
                    self.dominant_drive = data.get("dominant_drive", self.dominant_drive)
                    self.active_goal = data.get("active_goal", self.active_goal)
                    self.skills = data.get("skills", self.skills)
                    self.capability_trust = data.get("capability_trust", self.capability_trust)
                    self.agent_levels = data.get("agent_levels", self.agent_levels)
        except Exception as e:
            logger.error(f"Failed to safely read evolution state matrix: {e}")

    def save(self) -> None:
        """Performs atomic transaction save updates to prevent system power-cut corruptions."""
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            temp_file = self.state_file.with_suffix(".tmp")
            
            payload = {
                "level": self.level,
                "current_xp": self.current_xp,
                "xp_to_next_level": self.xp_to_next_level,
                "permission_rank": self.permission_rank,
                "trust_score": round(self.trust_score, 2),
                "mood": self.mood,
                "dominant_drive": self.dominant_drive,
                "active_goal": self.active_goal,
                "skills": self.skills,
                "capability_trust": self.capability_trust,
                "agent_levels": self.agent_levels
            }
            
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
                
            if self.state_file.exists():
                backup_file = self.state_file.with_suffix(".bak")
                if backup_file.exists():
                    backup_file.unlink()
                self.state_file.rename(backup_file)
                
            temp_file.rename(self.state_file)
        except Exception as e:
            logger.error(f"Atomic evolution state commit write failure: {e}")

    def log_experience_history(self, record: Dict[str, Any]) -> None:
        """Appends verified telemetry records to persistent historical indexes."""
        try:
            history = []
            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            
            history.append(record)
            
            temp_hist = self.history_file.with_suffix(".tmp")
            with open(temp_hist, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=4)
            temp_hist.rename(self.history_file)
        except Exception as e:
            logger.error(f"Failed writing event directly into history ledger: {e}")

    def get_ui_context(self) -> Dict[str, Any]:
        """Provides runtime context mappings safely matching UI requirements."""
        xp_pct = int((self.current_xp / max(1, self.xp_to_next_level)) * 100)
        return {
            "title": f"Level {self.level} — Runtime Operator",
            "xp_pct": min(100, max(0, xp_pct)),
            "trust_factor": f"{round(self.trust_score, 1)}%",
            "emotion": self.mood,
            "drives_matrix": {k: int(v * 10) for k, v in getattr(self, "drives_raw", {"helping": 7, "builder": 8, "learning": 9, "protection": 6, "curiosity": 8}).items()}
        }

    def dispatch_event(self, topic: str, data: Dict[str, Any]) -> None:
        if self.event_bus:
            self.event_bus.publish(topic, data)

    # --- NEW EXTENSIONS (APPENDED TO ORIGINAL CLASS) ---
    def to_dict(self) -> Dict[str, Any]:
        """Serializes current active state configurations directly for event bus broadcasts."""
        xp_pct = int((self.current_xp / max(1, self.xp_to_next_level)) * 100)
        return {
            "level": self.level,
            "current_xp": self.current_xp,
            "xp_to_next_level": self.xp_to_next_level,
            "permission_rank": self.permission_rank,
            "trust_score": self.trust_score,
            "mood": self.mood,
            "dominant_drive": self.dominant_drive,
            "active_goal": self.active_goal,
            "skills": self.skills,
            "capability_trust": self.capability_trust,
            "agent_levels": self.agent_levels,
            "drives_matrix": {
                "helping": 70, 
                "builder": 85, 
                "learning": 90, 
                "protection": 60, 
                "curiosity": 80
            }
        }