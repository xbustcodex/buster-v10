from buster.brain.tool_executor import ToolExecutor
from buster.brain.tool_router import ToolRouter


class RoutedAgentLoop:
    """
    Jarvis-style routed loop.

    This lets Buster choose a route first, execute the required tool, then ask
    the LLM to produce the final response with the gathered context.
    """

    def __init__(self, llm, router: ToolRouter | None = None, executor: ToolExecutor | None = None):
        self.llm = llm
        self.router = router or ToolRouter()
        self.executor = executor or ToolExecutor()

    def run(self, user_input: str) -> str:
        decision = self.router.decide(user_input)
        ctx = self.executor.execute(decision, user_input)

        prompt = f"""
You are Buster AI.

Route selected: {decision.tool}
Reason: {decision.reason}

CONTEXT:
{ctx.merged_context()}

USER:
{user_input}

Give the best answer.
"""
        return self.llm(prompt)
