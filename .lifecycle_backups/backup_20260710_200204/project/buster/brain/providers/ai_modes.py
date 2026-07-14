from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AIModeConfig:
    name: str
    system_prompt: str
    num_predict: int
    temperature: float
    timeout: int
    preferred_provider: str = "ollama"


class AIModeManager:
    """
    Central place for Buster's AI behavior modes.

    Instead of hardcoding one prompt/options set everywhere, Buster can switch:
    - voice: fast short replies
    - coding: longer precise engineering replies
    - research: deeper answers
    - default: balanced companion replies
    """

    MODES: Dict[str, AIModeConfig] = {
        "voice": AIModeConfig(
            name="voice",
            system_prompt=(
                "You are Buster, a desktop AI companion. "
                "For voice conversations, respond naturally, be concise, "
                "and keep most replies between 2 and 5 sentences. "
                "Only provide long explanations when the user explicitly asks for them."
            ),
            num_predict=180,
            temperature=0.3,
            timeout=120,
            preferred_provider="ollama",
        ),
        "coding": AIModeConfig(
            name="coding",
            system_prompt=(
                "You are Buster, a software engineering assistant. "
                "Be accurate, practical, and code-focused. "
                "Give complete code when useful, explain important decisions, "
                "and prefer safe, testable changes."
            ),
            num_predict=900,
            temperature=0.2,
            timeout=180,
            preferred_provider="ollama",
        ),
        "research": AIModeConfig(
            name="research",
            system_prompt=(
                "You are Buster, a research assistant. "
                "Give structured, detailed answers. Compare options when useful, "
                "explain tradeoffs, and separate facts from assumptions."
            ),
            num_predict=1200,
            temperature=0.4,
            timeout=240,
            preferred_provider="openrouter",
        ),
        "default": AIModeConfig(
            name="default",
            system_prompt=(
                "You are Buster, a desktop AI companion. "
                "Be direct, practical, and helpful."
            ),
            num_predict=400,
            temperature=0.3,
            timeout=120,
            preferred_provider="ollama",
        ),
    }

    def __init__(self, default_mode: str = "default"):
        self.current_mode = default_mode if default_mode in self.MODES else "default"

    def set_mode(self, mode: str) -> AIModeConfig:
        key = (mode or "").strip().lower()
        if key not in self.MODES:
            raise KeyError(f"Unknown AI mode: {mode}")
        self.current_mode = key
        return self.get_mode()

    def get_mode(self, mode: str | None = None) -> AIModeConfig:
        key = (mode or self.current_mode or "default").strip().lower()
        return self.MODES.get(key, self.MODES["default"])

    def names(self):
        return sorted(self.MODES.keys())

    def options(self, mode: str | None = None) -> dict:
        config = self.get_mode(mode)
        return {
            "num_predict": config.num_predict,
            "temperature": config.temperature,
        }

    def timeout(self, mode: str | None = None) -> int:
        return self.get_mode(mode).timeout

    def describe(self) -> str:
        config = self.get_mode()
        return (
            f"AI mode: {config.name}\n"
            f"Provider preference: {config.preferred_provider}\n"
            f"num_predict={config.num_predict}\n"
            f"temperature={config.temperature}\n"
            f"timeout={config.timeout}"
        )
