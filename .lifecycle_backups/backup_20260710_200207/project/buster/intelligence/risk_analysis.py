from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RiskReport:
    level: str
    risks: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "risks": self.risks,
            "blockers": self.blockers,
        }


class RiskAnalyzer:
    destructive_keywords = {
        "delete", "remove", "wipe", "format", "reset", "overwrite",
        "factory", "flash", "partition", "drop database"
    }

    def analyze(self, request: str = "", context: Dict[str, Any] | None = None) -> RiskReport:
        context = context or {}
        text = (request or "").lower()
        risks: List[str] = []
        blockers: List[str] = []

        if any(word in text for word in self.destructive_keywords):
            risks.append("destructive_action")
        if context.get("production"):
            risks.append("production_environment")
        if context.get("missing_tests"):
            risks.append("missing_tests")
        if context.get("unknown_project"):
            risks.append("unknown_project")
        if context.get("requires_credentials"):
            blockers.append("credentials_required")

        if blockers:
            level = "blocked"
        elif len(risks) >= 2:
            level = "high"
        elif risks:
            level = "medium"
        else:
            level = "low"

        return RiskReport(level, risks, blockers)
