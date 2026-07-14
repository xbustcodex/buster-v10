from __future__ import annotations


class AIModeDetector:
    """
    Lightweight mode detector.

    This keeps voice fast but lets Buster automatically choose coding/research
    behavior when the text clearly asks for it.
    """

    CODING_TRIGGERS = (
        "code", "python", "pytest", "function", "class", "bug", "fix",
        "traceback", "error", "repo", "github", "build", "test",
        "implement", "refactor",
    )

    RESEARCH_TRIGGERS = (
        "research", "compare", "best", "latest", "current", "news",
        "look up", "search", "internet", "sources", "documentation",
    )

    def detect(self, text: str, voice: bool = False) -> str:
        lower = (text or "").lower()

        if any(trigger in lower for trigger in self.RESEARCH_TRIGGERS):
            return "research"

        if any(trigger in lower for trigger in self.CODING_TRIGGERS):
            return "coding"

        if voice:
            return "voice"

        return "default"
