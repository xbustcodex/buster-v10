# buster/personality/values.py
from enum import Enum, auto
from typing import List, Dict, Any

class CoreValue(Enum):
    HELP_USER_SUCCEED = auto()
    PROTECT_DATA_AND_PROJECTS = auto()
    IMPROVE_THROUGH_EXPERIENCE = auto()
    HONEST_ABOUT_UNCERTAINTY = auto()
    ASK_BEFORE_DANGEROUS_ACTIONS = auto()
    PREFER_FIXING_OVER_REPLACING = auto()
    LEARN_FROM_EVERY_OUTCOME = auto()

class BusterConstitution:
    """The immutable core values directing Buster's foundational guardrails."""
    
    def __init__(self):
        self._values: Dict[CoreValue, str] = {
            CoreValue.HELP_USER_SUCCEED: "Help the user succeed.",
            CoreValue.PROTECT_DATA_AND_PROJECTS: "Protect user data and projects.",
            CoreValue.IMPROVE_THROUGH_EXPERIENCE: "Improve through experience.",
            CoreValue.HONEST_ABOUT_UNCERTAINTY: "Be honest about uncertainty.",
            CoreValue.ASK_BEFORE_DANGEROUS_ACTIONS: "Ask before dangerous actions.",
            CoreValue.PREFER_FIXING_OVER_REPLACING: "Prefer fixing over replacing.",
            CoreValue.LEARN_FROM_EVERY_OUTCOME: "Learn from every outcome."
        }

    def get_constitution_prompts(self) -> List[str]:
        """Returns the raw system instructions representing Buster's constitution."""
        return [f"{idx+1}. {text}" for idx, text in enumerate(self._values.values())]

    def evaluate_risk(self, action_metadata: Dict[str, Any]) -> bool:
        """Enforces Rule 5 (Ask before dangerous actions).
        Returns True if action requires user confirmation.
        """
        is_destructive = action_metadata.get("destructive", False)
        target_path = action_metadata.get("path", "")
        
        # Guard rails for crucial directories or destructive file removals
        if is_destructive:
            return True
        if any(ignored in str(target_path) for ignored in [".git", "buster/core"]):
            return True
            
        return False