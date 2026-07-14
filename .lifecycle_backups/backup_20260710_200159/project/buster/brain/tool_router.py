from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolDecision:
    tool: str
    reason: str
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRouter:
    """
    Buster v7.2 Tool Router.

    This is the decision layer that lets Buster choose whether to answer locally,
    use internet intelligence, inspect project state, or hand work to agents.
    """

    WEB_TRIGGERS = (
        "latest", "today", "current", "news", "price", "weather",
        "download", "documentation", "docs", "error code", "github",
        "release", "version", "search", "look up", "internet", "web",
        "online", "find", "research",
    )

    PROJECT_TRIGGERS = (
        "file", "folder", "project", "codebase", "repo", "repository",
        "import", "function", "class", "test", "pytest", "bug", "error",
        "traceback", "build", "run this", "fix this",
    )

    AGENT_TRIGGERS = (
        "build", "implement", "review", "verify", "plan", "task",
        "multi agent", "agent team", "tester", "builder", "fixer",
    )

    def decide(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> ToolDecision:
        text = (user_input or "").lower()
        context = context or {}

        if any(trigger in text for trigger in self.WEB_TRIGGERS):
            return ToolDecision(
                tool="web",
                reason="Request appears to need current or online information.",
                confidence=0.86,
            )

        if any(trigger in text for trigger in self.AGENT_TRIGGERS):
            return ToolDecision(
                tool="agent",
                reason="Request appears to need planning, building, testing, or verification.",
                confidence=0.78,
            )

        if any(trigger in text for trigger in self.PROJECT_TRIGGERS):
            return ToolDecision(
                tool="project",
                reason="Request appears related to local project/code inspection.",
                confidence=0.74,
            )

        return ToolDecision(
            tool="local",
            reason="Request can likely be handled from local reasoning or memory.",
            confidence=0.62,
        )
