from __future__ import annotations

from dataclasses import dataclass

from buster.voice.latency_config import VoiceLatencyConfig


@dataclass
class ListenResult:
    text: str
    ok: bool
    error: str = ""


class FastVoiceListener:
    """
    Low-latency SpeechRecognition listener.

    This does not replace your whole VoiceEngine. It is a safe helper you can
    call from listen_once or conversation mode.
    """

    def __init__(self, config: VoiceLatencyConfig | None = None, recognizer=None, microphone=None):
        self.config = config or VoiceLatencyConfig()
        self.recognizer = recognizer
        self.microphone = microphone

    def _ensure_sr(self):
        if self.recognizer is not None and self.microphone is not None:
            return self.recognizer, self.microphone

        import speech_recognition as sr

        self.recognizer = self.config.apply_to_recognizer(sr.Recognizer())
        self.microphone = sr.Microphone()
        return self.recognizer, self.microphone

    def listen_once(self) -> ListenResult:
        try:
            recognizer, microphone = self._ensure_sr()

            with microphone as source:
                audio = recognizer.listen(
                    source,
                    timeout=self.config.timeout,
                    phrase_time_limit=self.config.phrase_time_limit,
                )

            text = recognizer.recognize_google(audio).strip()
            return ListenResult(text=text, ok=bool(text))

        except Exception as exc:
            return ListenResult(text="", ok=False, error=str(exc))
