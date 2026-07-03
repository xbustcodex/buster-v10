from typing import List
import requests
from .models import WebSearchResult

class SearchProvider:
    name = "base"
    def search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        raise NotImplementedError

class DuckDuckGoInstantProvider(SearchProvider):
    """
    Zero-key starter provider. Limited, but safe for first integration.
    Later you can add Brave, SerpAPI, Tavily, GitHub, docs, or news providers.
    """
    name = "duckduckgo_instant"

    def search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()
        results = []

        abstract_url = data.get("AbstractURL") or data.get("AbstractSource")
        if data.get("AbstractText") and abstract_url:
            results.append(WebSearchResult(
                title=data.get("Heading") or query,
                url=abstract_url,
                snippet=data.get("AbstractText", ""),
                source=self.name,
                score=1.0,
            ))

        for topic in data.get("RelatedTopics", []):
            if len(results) >= max_results:
                break
            nested = topic.get("Topics", [topic]) if isinstance(topic, dict) else []
            for item in nested:
                if len(results) >= max_results:
                    break
                first_url = item.get("FirstURL")
                text = item.get("Text", "")
                if first_url and text:
                    results.append(WebSearchResult(
                        title=text.split(" - ")[0][:120],
                        url=first_url,
                        snippet=text,
                        source=self.name,
                        score=0.6,
                    ))
        return results[:max_results]
