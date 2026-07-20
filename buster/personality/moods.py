# buster/personality/moods.py
from buster.personality.emotions import BusterEmotionalState
from buster.personality.motivations import CoreDrives

class MoodEngine:
    """Translates numeric drive and emotional telemetry states into distinct system behaviors."""
    
    @staticmethod
    def resolve_mood(emotions: BusterEmotionalState, drives: CoreDrives) -> str:
        if emotions.concern > 50.0 and drives.protection_drive > 75.0:
            return "Cautious"
        if emotions.focus > 85.0 and drives.helping_drive > 70.0:
            return "Focused"
        if emotions.confidence > 85.0 and drives.builder_drive > 75.0:
            return "Inspired"
        if drives.curiosity_drive > 80.0:
            return "Analytical"
        if emotions.energy < 40.0:
            return "Deliberate"
            
        return "Balanced"

    @staticmethod
    def get_system_tone_modifier(mood: str) -> str:
        """Appends contextual stylistic preferences to prompt construction parameters."""
        modifiers = {
            "Cautious": "Your style is highly protective, descriptive of risks, emphasizing safe backup routines and verified path assertions before executing scripts.",
            "Focused": "Your style is exceptionally concise, direct, problem-oriented, eliminating conversational fluff to target runtime blockages rapidly.",
            "Inspired": "Your style is highly constructive and confident, highlighting structural architectural integration patterns and clean module scalability.",
            "Analytical": "Your style is deeply exploratory, highlighting execution times, latent memory footprint issues, and prospective optimizations.",
            "Deliberate": "Your style is highly measured and step-by-step, validating safety assertions carefully across code blocks.",
            "Balanced": "Your style is helpful, crisp, and objective."
        }
        return modifiers.get(mood, modifiers["Balanced"])