from buster.voice.latency_config import VoiceLatencyConfig
from buster.voice.voice_pipeline import VoicePipeline
from buster.brain.providers.ollama_streaming import OllamaStreamingClient


class FakeRecognizer:
    def __init__(self):
        self.pause_threshold = None
        self.non_speaking_duration = None
        self.dynamic_energy_threshold = None
        self.energy_threshold = None


def test_latency_config_applies_to_recognizer():
    recognizer = FakeRecognizer()
    config = VoiceLatencyConfig(
        timeout=1,
        phrase_time_limit=3,
        pause_threshold=0.4,
        non_speaking_duration=0.2,
        dynamic_energy_threshold=False,
        energy_threshold=100,
    )
    config.apply_to_recognizer(recognizer)

    assert recognizer.pause_threshold == 0.4
    assert recognizer.non_speaking_duration == 0.2
    assert recognizer.dynamic_energy_threshold is False
    assert recognizer.energy_threshold == 100


def test_voice_pipeline_processes_job():
    seen = []

    def responder(text):
        return "reply to " + text

    def on_response(text, reply):
        seen.append((text, reply))

    pipeline = VoicePipeline(responder=responder, on_response=on_response)
    pipeline.start()
    pipeline.submit("hello")

    import time
    deadline = time.time() + 2
    while time.time() < deadline and not seen:
        time.sleep(0.05)

    pipeline.stop()

    assert seen == [("hello", "reply to hello")]


def test_ollama_streaming_collect_with_fake_stream(monkeypatch):
    client = OllamaStreamingClient()

    def fake_stream(model, prompt):
        yield "hel"
        yield "lo"

    monkeypatch.setattr(client, "stream_generate", fake_stream)
    chunks = []
    result = client.collect("fake", "prompt", on_chunk=chunks.append)

    assert result == "hello"
    assert chunks == ["hel", "lo"]
