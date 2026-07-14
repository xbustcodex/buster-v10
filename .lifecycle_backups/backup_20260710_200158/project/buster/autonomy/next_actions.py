from __future__ import annotations

from typing import Any, Dict, List


class NextActionRecommender:
    """Rule-based next-action layer.

    This is deliberately simple and local. The AI planner can still use
    an LLM, but this layer gives Buster dependable OS-style defaults.
    """

    def recommend(self, context: Dict[str, Any]) -> Dict[str, Any]:
        request = (context.get("request") or "").lower()
        project_type = (context.get("project_type") or "general").lower()
        last_status = (context.get("last_status") or "").lower()
        error_count = int(context.get("error_count") or 0)
        has_tests = bool(context.get("has_tests", True))
        plugins = context.get("plugins") or []
        patterns = context.get("patterns") or []

        if "error" in request or "fix" in request or error_count > 0 or last_status == "failed":
            return self._action(
                "fix_then_verify",
                0.92,
                "Errors or failures detected, so Buster should repair first and verify after.",
                ["Fixer", "Tester", "Verifier"],
            )

        if "test" in request or not has_tests:
            return self._action(
                "create_or_run_tests",
                0.86,
                "Testing is the safest next step before deeper autonomy.",
                ["Tester", "Verifier"],
            )

        if any(word in request for word in ["build", "make", "create", "app", "project"]):
            return self._action(
                "plan_build_test_fix_verify",
                0.88,
                "Build request detected; use the full agent pipeline.",
                ["Builder", "Tester", "Fixer", "Reviewer", "Verifier"],
            )

        if any(word in request for word in ["review", "clean", "improve", "refactor"]):
            return self._action(
                "review_improve_verify",
                0.82,
                "Improvement request detected; review before changing code.",
                ["Reviewer", "Fixer", "Verifier"],
            )

        if project_type in ["android", "esp32", "arduino", "python"] and plugins:
            return self._action(
                "load_plugin_then_plan",
                0.78,
                "A matching plugin exists, so Buster should load capability-specific tools.",
                ["Planner", "Builder", "Verifier"],
            )

        if patterns:
            return self._action(
                "reuse_learned_pattern",
                0.74,
                "Relevant learned patterns exist, so reuse proven architecture first.",
                ["Planner", "Builder", "Reviewer"],
            )

        return self._action(
            "inspect_then_plan",
            0.65,
            "No urgent signal detected; inspect context before executing.",
            ["Planner", "Reviewer"],
        )

    def _action(self, name: str, confidence: float, reason: str, agents: List[str]) -> Dict[str, Any]:
        return {
            "action": name,
            "confidence": confidence,
            "reason": reason,
            "agents": agents,
        }
