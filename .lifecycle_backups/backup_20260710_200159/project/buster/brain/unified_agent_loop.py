from __future__ import annotations

from buster.brain.orchestrator import UnifiedIntelligenceOrchestrator


class UnifiedAgentLoop:
    """
    One conversation loop for typed chat, GUI, and voice.

    This should eventually replace separate logic paths that each decide
    differently how to use web/project/agent/local tools.
    """

    def __init__(self, ai_provider, orchestrator: UnifiedIntelligenceOrchestrator | None = None):
        self.ai_provider = ai_provider
        self.orchestrator = orchestrator or UnifiedIntelligenceOrchestrator()

    def run(self, user_input: str, *, voice: bool = False) -> str:
        result = self.orchestrator.orchestrate(user_input, voice=voice)
        mode = result.plan.ai_mode

        if hasattr(self.ai_provider, "complete"):
            return self.ai_provider.complete(
                user_input,
                context=result.context,
                mode=mode,
            )

        return result.context or "No response provider is configured."
