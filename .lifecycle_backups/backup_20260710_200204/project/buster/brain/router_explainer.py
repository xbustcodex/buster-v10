from __future__ import annotations

from buster.brain.orchestrator import OrchestrationPlan


class RouterExplainer:
    """
    Human-readable explanation of why Buster chose a route.
    Useful for debugging and a future 'why did you do that?' command.
    """

    def explain(self, plan: OrchestrationPlan) -> str:
        lines = [
            "Buster decision:",
            f"- Route: {plan.route}",
            f"- AI mode: {plan.ai_mode}",
            f"- Confidence: {int(plan.confidence * 100)}%",
            f"- Reason: {plan.reason}",
        ]

        if plan.should_use_web:
            lines.append("- Web: yes, request depends on online/current information.")
        if plan.should_use_project:
            lines.append("- Project: yes, request looks related to local code/workspace.")
        if plan.should_use_agents:
            lines.append("- Agents: yes, request looks like build/test/review work.")

        if not (plan.should_use_web or plan.should_use_project or plan.should_use_agents):
            lines.append("- Tools: no external tool required.")

        return "\n".join(lines)
