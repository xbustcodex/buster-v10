from buster.web.internet_service import InternetService

class WebBrain:
    """
    Brain-level interface for Buster internet intelligence.
    """
    def __init__(self, llm=None, internet_service=None):
        self.llm = llm
        self.internet = internet_service or InternetService()

    def needs_web(self, user_input: str) -> bool:
        return self.internet.should_use_web(user_input)

    def research(self, query: str):
        return self.internet.query(query)

    def process(self, user_input: str):
        if not self.needs_web(user_input):
            return None
        return self.research(user_input)
