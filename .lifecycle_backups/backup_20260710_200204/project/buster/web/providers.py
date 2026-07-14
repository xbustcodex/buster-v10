from dataclasses import dataclass
from typing import Dict, Type

from buster.web.search import DuckDuckGoInstantProvider, SearchProvider


@dataclass
class ProviderRegistry:
    """
    Registry for web providers.

    This lets Buster swap or add providers without rewriting the agents.
    """
    providers: Dict[str, Type[SearchProvider]]

    @classmethod
    def default(cls):
        return cls(providers={
            "duckduckgo_instant": DuckDuckGoInstantProvider,
        })

    def create(self, name: str) -> SearchProvider:
        if name not in self.providers:
            raise KeyError(f"Unknown provider: {name}")
        return self.providers[name]()

    def names(self):
        return sorted(self.providers.keys())
