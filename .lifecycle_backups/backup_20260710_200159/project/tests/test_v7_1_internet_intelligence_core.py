from buster.web.models import WebSearchResult
from buster.web.permissions import WebPermissions
from buster.web.source_ranker import rank_source
from buster.web.summarizer import simple_summarize
from buster.web.internet_service import InternetService

class FakeSearchProvider:
    name = "fake"
    def search(self, query, max_results=5):
        return [
            WebSearchResult(
                title="Example Docs",
                url="https://docs.example.com/guide",
                snippet="Useful documentation result for testing.",
                source=self.name,
            )
        ]

def test_permissions_block_bad_scheme():
    perms = WebPermissions()
    assert not perms.can_fetch_url("file:///etc/passwd")

def test_source_ranker_scores_docs():
    assert rank_source("https://docs.example.com/guide", "hello world " * 20) > 0.5

def test_summarizer_trims_text():
    text = "word " * 1000
    summary = simple_summarize(text, max_chars=100)
    assert len(summary) <= 103
    assert summary.endswith("...")

def test_internet_service_search_with_fake_provider():
    service = InternetService(search_provider=FakeSearchProvider())
    results = service.search("test query", max_results=1)
    assert len(results) == 1
    assert results[0].title == "Example Docs"

def test_internet_service_should_use_web():
    service = InternetService(search_provider=FakeSearchProvider())
    assert service.should_use_web("latest python release")
    assert not service.should_use_web("write a local poem")
