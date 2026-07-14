from __future__ import annotations

from buster.voice.fast_listener import FastVoiceListener
from buster.voice.latency_config import VoiceLatencyConfig
from buster.voice.voice_pipeline import VoicePipeline


class FastVoiceRuntime:
    """
    Glue layer for faster voice conversation.

    You can connect responder to Buster's brain.process and speaker to voice.speak.
    """

    def __init__(self, responder, speaker=None, on_response=None, config: VoiceLatencyConfig | None = None):
        self.listener = FastVoiceListener(config=config or VoiceLatencyConfig())
        self.pipeline = VoicePipeline(responder=responder, speaker=speaker, on_response=on_response)

    def start(self):
        return self.pipeline.start()

    def stop(self):
        return self.pipeline.stop()

    def listen_once_and_queue(self):
        result = self.listener.listen_once()
        if result.ok:
            self.pipeline.submit(result.text)
        return result
