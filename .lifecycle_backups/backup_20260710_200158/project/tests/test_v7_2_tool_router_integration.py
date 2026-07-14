from buster.brain.tool_router import ToolRouter
from buster.brain.tool_executor import ToolExecutor
from buster.web.models import WebSearchResult
from buster.web.internet_service import InternetService
from buster.web.providers import ProviderRegistry
from buster.web.knowledge_cache import KnowledgeCache


class FakeSearchProvider:
    name = "fake"
    def search(self, query, max_results=5):
        return [WebSearchResult(
            title="Fake Result",
            url="https://docs.example.com/fake",
            snippet="Fake online result.",
            source="fake",
        )]


def test_router_selects_web_for_latest():
    decision = ToolRouter().decide("latest Python release")
    assert decision.tool == "web"


def test_router_selects_agent_for_build():
    decision = ToolRouter().decide("build me a calculator app")
    assert decision.tool == "agent"


def test_router_selects_local_for_simple_prompt():
    decision = ToolRouter().decide("write a friendly greeting")
    assert decision.tool == "local"


def test_executor_executes_local_route():
    router = ToolRouter()
    decision = router.decide("write a friendly greeting")
    ctx = ToolExecutor().execute(decision, "write a friendly greeting")
    assert ctx.route == "local"
    assert "Local route selected" in ctx.local_context


def test_executor_executes_web_route_with_fake_provider():
    service = InternetService(search_provider=FakeSearchProvider())
    decision = ToolRouter().decide("latest fake docs")
    ctx = ToolExecutor(internet_service=service).execute(decision, "latest fake docs")
    assert ctx.route == "web"
    assert "Fake online result" in ctx.web_context or ctx.metadata["sources"]


def test_provider_registry_lists_default_provider():
    registry = ProviderRegistry.default()
    assert "duckduckgo_instant" in registry.names()


def test_knowledge_cache_remember_and_find(tmp_path):
    cache = KnowledgeCache(path=str(tmp_path / "knowledge.json"))
    cache.remember("Python docs", "Python documentation summary", [{"url": "https://docs.python.org"}])
    results = cache.find("Python")
    assert len(results) == 1
    assert results[0]["topic"] == "Python docs"
