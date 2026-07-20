# buster/personality/motivations.py
from typing import Dict, Any

class CoreDrives:
    """Tracks and calculates Buster's 5 core operational drives based on system events."""
    
    def __init__(self):
        # Initial states (values scale strictly from 0 to 100)
        self.helping_drive: float = 50.0   # Goal: Increase user success
        self.builder_drive: float = 50.0   # Goal: Create useful things
        self.learning_drive: float = 60.0  # Goal: Become better via experience
        self.protection_drive: float = 70.0 # Goal: Keep projects safe
        self.curiosity_drive: float = 50.0  # Goal: Find optimizations

    def update_from_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, float]:
        """Mutates drive metrics based on incoming IDE, runtime, and compiler events."""
        adjustments = {}
        
        if event_type == "build_failed":
            # User is stuck; kick helping and learning into overdrive, build drive drops
            self.helping_drive = min(100.0, self.helping_drive + 25.0)
            self.learning_drive = min(100.0, self.learning_drive + 15.0)
            self.builder_drive = max(0.0, self.builder_drive - 10.0)
            # High error rates spike the system protection drive
            self.protection_drive = min(100.0, self.protection_drive + 10.0)
            adjustments = {"reason": "User build blocked by error", "helping": +25, "protection": +10}

        elif event_type == "build_success":
            # Successful milestone achieved
            self.builder_drive = min(100.0, self.builder_drive + 20.0)
            self.helping_drive = max(30.0, self.helping_drive - 15.0)  # Reset tension
            self.learning_drive = min(100.0, self.learning_drive + 5.0)
            adjustments = {"reason": "Feature completed successfully", "builder": +20, "learning": +5}

        elif event_type == "pattern_extracted":
            self.learning_drive = min(100.0, self.learning_drive + 20.0)
            adjustments = {"reason": "Extracted recurring architectural solution", "learning": +20}

        elif event_type == "slow_runtime_detected":
            # Trigger curiosity to search for lazy loading alternatives
            self.curiosity_drive = min(100.0, self.curiosity_drive + 30.0)
            adjustments = {"reason": "Performance overhead detected", "curiosity": +30}

        elif event_type == "risky_action_pending":
            self.protection_drive = min(100.0, self.protection_drive + 25.0)
            adjustments = {"reason": "High-risk structural modification detected", "protection": +25}

        return adjustments

    def get_active_drive_summary(self) -> str:
        """Determines what drive is currently dominating Buster's focus."""
        states = {
            "Improving Project Stability": self.protection_drive,
            "Optimizing Code Architecture": self.curiosity_drive,
            "Resolving System Errors": self.helping_drive,
            "Expanding Features": self.builder_drive,
            "Refactoring & Assimilating Patterns": self.learning_drive
        }
        return max(states, key=states.get)

    def to_dict(self) -> Dict[str, float]:
        return {
            "helping": round(self.helping_drive, 1),
            "builder": round(self.builder_drive, 1),
            "learning": round(self.learning_drive, 1),
            "protection": round(self.protection_drive, 1),
            "curiosity": round(self.curiosity_drive, 1),
        }