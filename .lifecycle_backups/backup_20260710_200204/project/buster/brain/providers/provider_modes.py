from __future__ import annotations

from buster.brain.providers.ai_modes import AIModeManager
from buster.brain.providers.mode_detector import AIModeDetector


class ProviderModeController:
    """
    Controller that can be used by AIProviderManager or BrainEngine.

    It gives Buster one place to:
    - set AI mode manually
    - auto-detect AI mode from a request
    - describe active mode
    """

    def __init__(self):
        self.mode_manager = AIModeManager()
        self.detector = AIModeDetector()

    def set_mode(self, mode: str) -> str:
        config = self.mode_manager.set_mode(mode)
        return f"AI mode set to {config.name}."

    def auto_mode_for(self, text: str, voice: bool = False) -> str:
        mode = self.detector.detect(text, voice=voice)
        self.mode_manager.set_mode(mode)
        return mode

    def status(self) -> str:
        return self.mode_manager.describe()
