class AgentLoop:
    """
    Optional Jarvis-style loop.
    Do not replace your whole Buster loop immediately. Connect this behind
    one command first, then promote it later.
    """
    def __init__(self, llm, web_brain):
        self.llm = llm
        self.web_brain = web_brain

    def run(self, user_input: str) -> str:
        web_result = self.web_brain.process(user_input)
        web_context = web_result.answer if web_result else ""
        prompt = f"""
You are Buster AI.

Use web context only if useful.

WEB CONTEXT:
{web_context}

USER:
{user_input}

ANSWER:
"""
        return self.llm(prompt)
