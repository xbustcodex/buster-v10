from buster.web.internet_service import InternetService

class ResearchEngine:
    """
    Multi-step research wrapper.
    v7.1 starts simple. Later this can expand into:
    search -> compare -> fetch docs -> cite -> save memory.
    """
    def __init__(self, internet_service: InternetService | None = None):
        self.internet = internet_service or InternetService()

    def research(self, topic: str, depth: int = 1):
        result = self.internet.query(topic, max_results=max(3, depth * 3))
        return {
            "topic": topic,
            "summary": result.answer,
            "sources": [
                {"title": src.title, "url": src.url, "snippet": src.snippet}
                for src in result.sources
            ],
        }
