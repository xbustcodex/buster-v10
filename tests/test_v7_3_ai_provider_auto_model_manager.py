from buster.brain.providers.ollama_models import OllamaModelInfo, OllamaModelManager
from buster.brain.providers.provider_diagnostics import ProviderDiagnostics


class FakeManager(OllamaModelManager):
    def __init__(self, names):
        super().__init__()
        self.names = names

    def list_models(self):
        return [OllamaModelInfo(name=name) for name in self.names]


def test_choose_preferred_model_when_installed():
    manager = FakeManager(["qwen2.5-coder:3b", "llama3.2"])
    assert manager.choose_model("llama3.2") == "llama3.2"


def test_choose_coder_model_first():
    manager = FakeManager(["llama3.2", "qwen2.5-coder:3b"])
    assert manager.choose_model() == "qwen2.5-coder:3b"


def test_choose_first_model_when_no_coder():
    manager = FakeManager(["mistral:7b", "llama3.2"])
    assert manager.choose_model() == "mistral:7b"


def test_fallback_when_no_models():
    manager = FakeManager([])
    assert manager.choose_model() == "llama3.2"


def test_status_text_not_running():
    manager = FakeManager([])
    manager.is_running = lambda: False
    manager.last_error = "connection refused"
    text = manager.status_text()
    assert "not running" in text
    assert "connection refused" in text


def test_provider_diagnostics_report_shape(monkeypatch):
    class StaticManager(FakeManager):
        def is_running(self):
            return True

    import buster.brain.providers.provider_diagnostics as module
    monkeypatch.setattr(module, "OllamaModelManager", lambda: StaticManager(["qwen2.5-coder:3b"]))

    report = ProviderDiagnostics().report()
    assert "AI Provider Diagnostics" in report
    assert "qwen2.5-coder:3b" in report
