from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from buster.voice.fast_listener import FastVoiceListener
from buster.voice.latency_config import VoiceLatencyConfig
from buster.voice.voice_pipeline import VoicePipeline


class FastVoiceRuntime:
    """
    Glue layer for faster voice conversation.
    Connects responder to Buster's brain.process and speaker to voice.speak.
    """

    def __init__(
        self,
        responder: Callable[[str], Any],
        speaker: Optional[Callable[[str], Any]] = None,
        on_response: Optional[Callable[[str], Any]] = None,
        config: VoiceLatencyConfig | None = None,
    ):
        self.listener = FastVoiceListener(config=config or VoiceLatencyConfig())
        self.pipeline = VoicePipeline(
            responder=responder, speaker=speaker, on_response=on_response
        )

    def start(self):
        return self.pipeline.start()

    def stop(self):
        return self.pipeline.stop()

    def listen_once_and_queue(self, async_run: bool = True):
        if not async_run:
            return self._listen_and_submit()

        thread = threading.Thread(target=self._listen_and_submit, daemon=True)
        thread.start()
        return thread

    def _listen_and_submit(self):
        result = self.listener.listen_once()
        if getattr(result, "ok", False) and getattr(result, "text", None):
            self.pipeline.submit(result.text)
        return result