from __future__ import annotations

from buster.web.knowledge_cache import KnowledgeCache
from buster.web.models import WebResult


class ResearchMemoryBridge:
    """
    Saves useful web research into the long-term web knowledge cache.
    """

    def __init__(self, cache: KnowledgeCache | None = None):
        self.cache = cache or KnowledgeCache()

    def remember_result(self, result: WebResult) -> str:
        if not result.used_web or not result.answer:
            return "No web result to remember."

        self.cache.remember(
            topic=result.query,
            summary=result.answer,
            sources=[
                {"title": src.title, "url": src.url, "snippet": src.snippet}
                for src in result.sources
            ],
        )
        return f"Remembered web research for: {result.query}"
