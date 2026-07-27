from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

from .audio_backends import EdgeTTSBackend, VADBackend, WhisperBackend


class VoiceService:
    """Runtime-owned speech-to-text and text-to-speech service."""

    def __init__(
        self,
        runtime_core: Any,
        *,
        project_root: str | Path | None = None,
        whisper_model: str = "base",
    ):
        self.runtime_core = runtime_core
        self.dispatcher = getattr(runtime_core, "dispatcher", None)
        self.project_root = Path(
            project_root or getattr(runtime_core, "root", ".")
        ).resolve()

        self.whisper = WhisperBackend(model_size=whisper_model)
        self.vad = VADBackend()
        self.edge_tts = EdgeTTSBackend()

        self._pyttsx3 = None
        self._started = False
        self._subscriptions: list[Any] = []

        self._active_transcriptions: set[str] = set()
        self._transcription_guard = threading.RLock()

        self._speech_guard = threading.RLock()
        self._speech_generation = 0
        self._speaking = False

        self.last_error = ""

        if pyttsx3 is not None:
            try:
                self._pyttsx3 = pyttsx3.init()
            except Exception as exc:
                self.last_error = str(exc)

        self._subscribe_events()

    @property
    def running(self) -> bool:
        return self._started

    @property
    def configured(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        return True

    def start(self) -> dict[str, Any]:
        if self._started:
            return self.status()

        self._started = True
        self._publish("audio.service.started", self.status())

        threading.Thread(
            target=self._warm_whisper_model,
            daemon=True,
            name="BusterWhisperWarmup",
        ).start()

        return self.status()

    def stop(self) -> dict[str, Any]:
        if not self._started:
            return self.status()

        self.stop_speaking(reason="voice_service_stopped")
        self._started = False
        self._publish("audio.service.stopped", self.status())
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "status": "running" if self._started else "ready",
            "running": self._started,
            "configured": True,
            "available": True,
            "whisper": self.whisper.status(),
            "vad": self.vad.status(),
            "edge_tts": self.edge_tts.status(),
            "pyttsx3": {
                "available": self._pyttsx3 is not None,
            },
            "speaking": self._speaking,
            "interruptible_playback": self.edge_tts.interruptible,
            "last_error": self.last_error,
        }

    def transcribe(
        self,
        audio_file: str | Path,
        *,
        language: str | None = None,
        require_speech: bool = True,
        fast_mode: bool = True,
    ) -> dict[str, Any]:
        path = Path(audio_file).expanduser().resolve()
        path_key = str(path).lower()

        self._publish(
            "audio.transcription.started",
            {"audio_file": str(path)},
        )

        try:
            if require_speech and not self.vad.has_speech(path):
                result = {
                    "text": "",
                    "audio_file": str(path),
                    "speech_detected": False,
                    "backend": self.vad.backend,
                }
                self._publish(
                    "audio.transcription.completed",
                    result,
                )
                return result

            result = self.whisper.transcribe(
                path,
                language=language,
                vad_filter=True,
                fast_mode=fast_mode,
            )
            result["audio_file"] = str(path)
            result["speech_detected"] = True

            self._publish(
                "audio.transcription.completed",
                result,
            )
            self._publish(
                "voice.transcribed",
                {
                    "text": result.get("text", ""),
                    "file": str(path),
                    "backend": result.get("backend"),
                },
            )
            return result

        except Exception as exc:
            self.last_error = str(exc)
            self._publish(
                "audio.error",
                {
                    "operation": "transcribe",
                    "audio_file": str(path),
                    "error": str(exc),
                },
            )
            return {
                "text": "",
                "audio_file": str(path),
                "speech_detected": None,
                "error": str(exc),
            }

        finally:
            with self._transcription_guard:
                self._active_transcriptions.discard(path_key)

    def transcribe_async(
        self,
        audio_file: str | Path,
        **kwargs: Any,
    ) -> threading.Thread | None:
        path = Path(audio_file).expanduser().resolve()
        path_key = str(path).lower()

        with self._transcription_guard:
            if path_key in self._active_transcriptions:
                self._publish(
                    "audio.transcription.duplicate_ignored",
                    {"audio_file": str(path)},
                )
                return None

            self._active_transcriptions.add(path_key)

        thread = threading.Thread(
            target=self.transcribe,
            args=(path,),
            kwargs=kwargs,
            daemon=True,
            name="BusterVoiceTranscription",
        )
        thread.start()
        return thread

    def speak(
        self,
        text: str,
        *,
        voice: str | None = None,
        rate: str | int | None = None,
        volume: str | int | float | None = None,
        prefer_edge: bool = True,
    ) -> dict[str, Any]:
        clean_text = str(text or "").strip()
        if not clean_text:
            raise ValueError("No text supplied for speech synthesis.")

        with self._speech_guard:
            self._speech_generation += 1
            generation = self._speech_generation
            self._speaking = True

        self._publish(
            "audio.tts.started",
            {
                "text": clean_text,
                "generation": generation,
            },
        )

        try:
            interrupted = False

            if (
                prefer_edge
                and self.edge_tts.available
                and self.edge_tts.playback_available
            ):
                output = (
                    self.project_root
                    / "recordings"
                    / "tts"
                    / f"buster_voice_{generation}.mp3"
                )

                path = self.edge_tts.synthesize(
                    clean_text,
                    output,
                    voice=voice,
                    rate=self._edge_rate(rate),
                    volume=self._edge_volume(volume),
                )

                with self._speech_guard:
                    cancelled_before_playback = (
                        generation != self._speech_generation
                    )

                if cancelled_before_playback:
                    result = {
                        "backend": "edge-tts",
                        "output_file": str(path),
                        "text": clean_text,
                        "interrupted": True,
                        "reason": "cancelled_before_playback",
                    }
                    self._publish("audio.tts.interrupted", result)
                    return result

                playback = self.edge_tts.play(path)
                interrupted = bool(playback.get("interrupted"))

                result = {
                    "backend": "edge-tts",
                    "playback_backend": playback.get("backend"),
                    "output_file": str(path),
                    "text": clean_text,
                    "interrupted": interrupted,
                }

            elif self._pyttsx3 is not None:
                if isinstance(rate, int):
                    self._pyttsx3.setProperty("rate", rate)

                if isinstance(volume, (int, float)):
                    self._pyttsx3.setProperty(
                        "volume",
                        max(0.0, min(1.0, float(volume))),
                    )

                self._pyttsx3.say(clean_text)
                self._pyttsx3.runAndWait()

                with self._speech_guard:
                    interrupted = (
                        generation != self._speech_generation
                    )

                result = {
                    "backend": "pyttsx3",
                    "output_file": None,
                    "text": clean_text,
                    "interrupted": interrupted,
                }

            else:
                raise RuntimeError("No TTS backend available.")

            if interrupted:
                self._publish("audio.tts.interrupted", result)
            else:
                self._publish("audio.tts.completed", result)

            return result

        except Exception as exc:
            self.last_error = str(exc)
            self._publish(
                "audio.error",
                {
                    "operation": "tts",
                    "error": str(exc),
                },
            )
            raise

        finally:
            with self._speech_guard:
                if generation == self._speech_generation:
                    self._speaking = False

    def speak_async(
        self,
        text: str,
        **kwargs: Any,
    ) -> threading.Thread:
        thread = threading.Thread(
            target=self.speak,
            args=(text,),
            kwargs=kwargs,
            daemon=True,
            name="BusterVoiceTTS",
        )
        thread.start()
        return thread

    def stop_speaking(
        self,
        *,
        reason: str = "requested",
    ) -> bool:
        with self._speech_guard:
            was_speaking = self._speaking
            self._speech_generation += 1
            self._speaking = False

        edge_stopped = self.edge_tts.stop()

        if self._pyttsx3 is not None:
            try:
                self._pyttsx3.stop()
            except Exception:
                pass

        if was_speaking:
            self._publish(
                "audio.tts.interrupted",
                {
                    "reason": reason,
                    "edge_stopped": edge_stopped,
                },
            )

        return was_speaking

    def _warm_whisper_model(self) -> None:
        try:
            self._publish(
                "audio.whisper.warmup.started",
                {"model": self.whisper.model_size},
            )
            self.whisper.preload()
            self._publish(
                "audio.whisper.warmup.completed",
                {
                    "model": self.whisper.model_size,
                    "backend": self.whisper.status().get("backend"),
                },
            )
        except Exception as exc:
            self.last_error = str(exc)
            self._publish(
                "audio.whisper.warmup.failed",
                {"error": str(exc)},
            )

    def _subscribe_events(self) -> None:
        subscribe = getattr(self.dispatcher, "subscribe", None)
        if not callable(subscribe):
            return

        handlers = {
            "audio.transcribe.requested": self._handle_transcribe,
            "audio.tts.requested": self._handle_tts,
            "audio.tts.stop.requested": self._handle_tts_stop,
        }

        for topic, handler in handlers.items():
            try:
                unsubscribe = subscribe(topic, handler)
                if callable(unsubscribe):
                    self._subscriptions.append(unsubscribe)
            except Exception:
                continue

    def _handle_transcribe(self, event: Any) -> None:
        payload = self._payload(event)
        path = (
            payload.get("audio_file")
            or payload.get("file")
            or payload.get("path")
        )

        if not path:
            self._publish(
                "audio.error",
                {
                    "operation": "transcribe",
                    "error": "audio_file is required",
                },
            )
            return

        self.transcribe_async(
            path,
            language=payload.get("language"),
            require_speech=payload.get(
                "require_speech",
                True,
            ),
            fast_mode=payload.get(
                "fast_mode",
                True,
            ),
        )

    def _handle_tts(self, event: Any) -> None:
        payload = self._payload(event)
        text = payload.get("text") or payload.get("message")

        if not text:
            self._publish(
                "audio.error",
                {
                    "operation": "tts",
                    "error": "text is required",
                },
            )
            return

        self.speak_async(
            text,
            voice=payload.get("voice"),
            rate=payload.get("rate"),
            volume=payload.get("volume"),
            prefer_edge=payload.get(
                "prefer_edge",
                True,
            ),
        )

    def _handle_tts_stop(self, event: Any) -> None:
        payload = self._payload(event)
        self.stop_speaking(
            reason=payload.get(
                "reason",
                "tts_stop_requested",
            ),
        )

    def _publish(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> None:
        publish = getattr(self.dispatcher, "publish", None)
        if not callable(publish):
            return

        try:
            publish(
                topic,
                payload,
                source="voice_service",
            )
        except TypeError:
            publish(topic, payload)

    @staticmethod
    def _payload(event: Any) -> dict[str, Any]:
        if isinstance(event, dict):
            value = event.get("payload", event)
            return value if isinstance(value, dict) else {}

        value = getattr(event, "payload", None)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _edge_rate(
        rate: str | int | None,
    ) -> str:
        if rate is None:
            return "+0%"

        if isinstance(rate, str):
            return rate

        return f"{int(((int(rate) - 180) / 180) * 100):+d}%"

    @staticmethod
    def _edge_volume(
        volume: str | int | float | None,
    ) -> str:
        if volume is None:
            return "+0%"

        if isinstance(volume, str):
            return volume

        value = float(volume)
        percentage = (
            int((value - 1.0) * 100)
            if value <= 1
            else int(value - 100)
        )
        return f"{percentage:+d}%"
