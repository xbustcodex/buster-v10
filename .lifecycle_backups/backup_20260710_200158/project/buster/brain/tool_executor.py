from buster.brain.tool_context import ToolContext
from buster.brain.tool_router import ToolDecision
from buster.web.internet_service import InternetService


class ToolExecutor:
    """
    Executes the chosen route.

    v7.2 only fully executes web/local safely. Project and agent routes return
    structured placeholders so they can be wired into your existing Buster
    project indexer and agent team without breaking current tests.
    """

    def __init__(self, internet_service: InternetService | None = None):
        self.internet = internet_service or InternetService()

    def execute(self, decision: ToolDecision, user_input: str) -> ToolContext:
        ctx = ToolContext(user_input=user_input, route=decision.tool)
        ctx.metadata["decision_reason"] = decision.reason
        ctx.metadata["decision_confidence"] = decision.confidence

        if decision.tool == "web":
            result = self.internet.query(user_input)
            ctx.web_context = result.answer
            ctx.metadata["sources"] = [
                {"title": src.title, "url": src.url, "snippet": src.snippet}
                for src in result.sources
            ]
            return ctx

        if decision.tool == "project":
            ctx.project_context = (
                "Project route selected. Connect this to Buster's existing "
                "workspace awareness, project index, files, tests, and build tools."
            )
            return ctx

        if decision.tool == "agent":
            ctx.agent_notes.append(
                "Agent route selected. Connect this to Builder, Tester, Fixer, Reviewer, and Verifier agents."
            )
            return ctx

        ctx.local_context = "Local route selected. No external tool required."
        return ctx
