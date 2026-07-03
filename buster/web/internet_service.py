from typing import List
from .cache import WebCache
from .fetch import WebFetcher
from .models import WebResult, WebSearchResult
from .permissions import WebPermissions
from .search import DuckDuckGoInstantProvider, SearchProvider
from .source_ranker import rank_source
from .summarizer import simple_summarize

class InternetService:
    """
    Shared internet service for all Buster agents.
    Agents should call this instead of directly using requests/search providers.
    """
    def __init__(self, search_provider: SearchProvider | None = None,
                 permissions: WebPermissions | None = None,
                 cache: WebCache | None = None):
        self.permissions = permissions or WebPermissions()
        self.search_provider = search_provider or DuckDuckGoInstantProvider()
        self.cache = cache or WebCache()
        self.fetcher = WebFetcher(permissions=self.permissions)

    def should_use_web(self, prompt: str) -> bool:
        text = prompt.lower()
        triggers = [
            "latest", "today", "current", "news", "price", "weather",
            "download", "documentation", "docs", "error code",
            "github", "release", "version", "search", "look up",
        ]
        return any(trigger in text for trigger in triggers)

    def search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        if not self.permissions.can_search():
            return []
        cache_key = f"search:{query}:{max_results}"
        cached = self.cache.get(cache_key)
        if cached:
            return [WebSearchResult(**item) for item in cached]
        results = self.search_provider.search(query, max_results=max_results)
        for result in results:
            result.score = max(result.score, rank_source(result.url, result.snippet))
        results.sort(key=lambda r: r.score, reverse=True)
        self.cache.set(cache_key, [r.__dict__ for r in results])
        return results

    def query(self, query: str, max_results: int = 5, fetch_pages: bool = True) -> WebResult:
        if not self.permissions.can_search():
            return WebResult(query=query, answer="Internet access is disabled.", used_web=False)

        results = self.search(query, max_results=max_results)
        pages = []

        if fetch_pages:
            for result in results[: self.permissions.max_pages_per_query]:
                page = self.fetcher.fetch(result.url)
                if page.text:
                    pages.append(page)

        if pages:
            combined = "\n\n".join(f"Source: {page.title or page.url}\n{page.text}" for page in pages)
            answer = simple_summarize(combined)
        elif results:
            combined = "\n".join(f"{r.title}: {r.snippet}" for r in results)
            answer = simple_summarize(combined)
        else:
            answer = "No useful web results found."

        return WebResult(query=query, answer=answer, used_web=True, sources=results, pages=pages,
                         notes=["v7.1 internet service result"])
