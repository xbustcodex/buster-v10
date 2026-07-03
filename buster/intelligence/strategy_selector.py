from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Strategy:
    name: str
    steps: List[str] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    plugins: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "steps": self.steps,
            "agents": self.agents,
            "plugins": self.plugins,
            "reason": self.reason,
        }


class StrategySelector:
    def select(self, request: str = "", context: Dict[str, Any] | None = None) -> Strategy:
        context = context or {}
        text = (request or "").lower()

        if "android" in text or context.get("project_type") == "android":
            return Strategy(
                "android_build_verify",
                ["load_android_plugin", "inspect_project", "build", "test", "fix_if_needed", "verify"],
                ["builder", "tester", "fixer", "reviewer", "verifier"],
                ["android"],
                "Android project detected.",
            )

        if "esp32" in text or "arduino" in text or context.get("project_type") in {"esp32", "arduino"}:
            return Strategy(
                "embedded_build_verify",
                ["load_embedded_plugin", "inspect_sketch", "compile", "fix_if_needed", "verify"],
                ["builder", "tester", "fixer", "verifier"],
                ["esp32", "arduino"],
                "Embedded hardware project detected.",
            )

        if "gui" in text or "desktop" in text or "tkinter" in text:
            return Strategy(
                "desktop_gui_behavioral",
                ["inspect_project", "build", "run_gui", "behavioral_test", "fix_if_needed", "verify"],
                ["builder", "tester", "fixer", "reviewer", "verifier"],
                ["python"],
                "Desktop GUI task detected.",
            )

        return Strategy(
            "general_safe_build",
            ["inspect", "plan", "build", "test", "fix_if_needed", "review", "verify", "learn"],
            ["builder", "tester", "fixer", "reviewer", "verifier"],
            [],
            "Default safe software build strategy.",
        )
