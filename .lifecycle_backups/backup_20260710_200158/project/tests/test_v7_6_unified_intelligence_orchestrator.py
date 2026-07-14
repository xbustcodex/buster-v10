from buster.brain.orchestrator import UnifiedIntelligenceOrchestrator
from buster.brain.router_explainer import RouterExplainer
from buster.brain.unified_agent_loop import UnifiedAgentLoop
from buster.brain.conversation_runtime import UnifiedConversationRuntime


class FakeAIProvider:
    def __init__(self):
        self.calls = []

    def complete(self, prompt, context="", mode=None):
        self.calls.append({"prompt": prompt, "context": context, "mode": mode})
        return f"mode={mode} prompt={prompt}"


def test_orchestrator_web_route_uses_research_mode():
    orchestrator = UnifiedIntelligenceOrchestrator()
    plan = orchestrator.make_plan("latest Python release")
    assert plan.route == "web"
    assert plan.ai_mode == "research"
    assert plan.should_use_web is True


def test_orchestrator_voice_route_uses_voice_mode():
    orchestrator = UnifiedIntelligenceOrchestrator()
    plan = orchestrator.make_plan("how are you today", voice=True)
    assert plan.ai_mode == "voice"


def test_orchestrator_agent_route_uses_coding_mode():
    orchestrator = UnifiedIntelligenceOrchestrator()
    plan = orchestrator.make_plan("build me a calculator app")
    assert plan.route == "agent"
    assert plan.ai_mode == "coding"


def test_router_explainer_mentions_route_and_mode():
    orchestrator = UnifiedIntelligenceOrchestrator()
    plan = orchestrator.make_plan("latest AI news")
    text = RouterExplainer().explain(plan)
    assert "Route: web" in text
    assert "AI mode: research" in text


def test_unified_agent_loop_passes_mode_to_provider():
    provider = FakeAIProvider()
    loop = UnifiedAgentLoop(provider)
    reply = loop.run("how are you", voice=True)
    assert "mode=voice" in reply
    assert provider.calls[-1]["mode"] == "voice"


def test_unified_conversation_runtime_records_history():
    provider = FakeAIProvider()
    runtime = UnifiedConversationRuntime(provider, max_turns=4)
    reply = runtime.ask("hello", voice=True)
    assert reply
    assert len(runtime.history) == 2
    assert runtime.history[0].role == "user"


def test_unified_conversation_runtime_clear():
    provider = FakeAIProvider()
    runtime = UnifiedConversationRuntime(provider)
    runtime.ask("hello")
    assert runtime.clear() == "Conversation context cleared."
    assert runtime.history == []
