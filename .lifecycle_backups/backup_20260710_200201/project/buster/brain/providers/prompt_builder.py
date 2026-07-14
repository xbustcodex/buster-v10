from __future__ import annotations

from buster.brain.providers.ai_modes import AIModeManager


class PromptBuilder:
    """
    Builds prompts for AI providers using centralized mode configs.
    """

    def __init__(self, mode_manager: AIModeManager | None = None):
        self.mode_manager = mode_manager or AIModeManager()

    def build(self, user_prompt: str, context: str = "", mode: str | None = None) -> str:
        config = self.mode_manager.get_mode(mode)
        return (
            f"{config.system_prompt}\n\n"
            f"Context:\n{context}\n\n"
            f"User:\n{user_prompt}\n\n"
            "Buster:"
        )
