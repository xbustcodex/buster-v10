from __future__ import annotations

import queue
from concurrent.futures import ThreadPoolExecutor
import tempfile
import threading
import time
import wave
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

try:
    import pyaudio
except ImportError:
    pyaudio = None


class StreamingSTTService:
    """
    Continuous microphone-to-Whisper service.

    Audio is captured in short frames. VAD determines when speech begins and
    ends. Completed utterances are written to a temporary WAV file and passed
    to the existing runtime VoiceService for local Whisper transcription.
    """

    def __init__(
        self,
        runtime_core: Any,
        voice_service: Any,
        wake_word_service: Any | None = None,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
        frame_ms: int = 30,
        silence_ms: int = 450,
        pre_roll_ms: int = 180,
        max_utterance_seconds: float = 20.0,
    ):
        self.runtime_core = runtime_core
        self.dispatcher = getattr(runtime_core, "dispatcher", None)
        self.voice_service = voice_service
        self.wake_word_service = wake_word_service

        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.frame_ms = int(frame_ms)
        self.frames_per_buffer = int(
            self.sample_rate * self.frame_ms / 1000
        )
        self.silence_frames_required = max(
            1,
            int(silence_ms / self.frame_ms),
        )
        self.pre_roll_frames = max(
            1,
            int(pre_roll_ms / self.frame_ms),
        )
        self.max_utterance_frames = max(
            1,
            int(
                max_utterance_seconds
                * 1000
                / self.frame_ms
            ),
        )

        self._audio = None
        self._stream = None
        self._capture_thread = None
        self._worker_thread = None
        self._running = False
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=256)
        self._subscriptions = []
        self._lock = threading.RLock()
        self._transcription_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="BusterWhisper",
        )
        self._pending_transcriptions = 0
        self.last_error = ""

        self._subscribe_events()

    @property
    def available(self) -> bool:
        return pyaudio is not None

    @property
    def configured(self) -> bool:
        return self.available

    @property
    def running(self) -> bool:
        return self._running

    def status(self) -> dict[str, Any]:
        return {
            "status": (
                "running"
                if self._running
                else "ready"
                if self.available
                else "not_installed"
            ),
            "running": self._running,
            "available": self.available,
            "configured": self.configured,
            "sample_rate": self.sample_rate,
            "frame_ms": self.frame_ms,
            "silence_ms": (
                self.silence_frames_required
                * self.frame_ms
            ),
            "pending_transcriptions": self._pending_transcriptions,
            "last_error": self.last_error,
        }

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._running:
                return self.status()

            if pyaudio is None:
                raise RuntimeError(
                    "PyAudio is required for streaming STT."
                )

            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.frames_per_buffer,
            )

            self._running = True
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True,
                name="BusterStreamingCapture",
            )
            self._worker_thread = threading.Thread(
                target=self._speech_loop,
                daemon=True,
                name="BusterStreamingSTT",
            )
            self._capture_thread.start()
            self._worker_thread.start()

        self._publish(
            "audio.streaming.started",
            self.status(),
        )
        self._publish(
            "voice.status",
            {
                "status": "listening",
                "mode": "streaming",
            },
        )
        return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if not self._running:
                return self.status()

            self._running = False
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass

            if self._stream is not None:
                try:
                    self._stream.stop_stream()
                except Exception:
                    pass
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            if self._audio is not None:
                try:
                    self._audio.terminate()
                except Exception:
                    pass
                self._audio = None

        self._publish(
            "audio.streaming.stopped",
            self.status(),
        )
        self._publish(
            "voice.status",
            {
                "status": "ready",
                "mode": "streaming",
            },
        )
        return self.status()

    def _capture_loop(self) -> None:
        while self._running:
            try:
                data = self._stream.read(
                    self.frames_per_buffer,
                    exception_on_overflow=False,
                )
                try:
                    self._queue.put(data, timeout=0.2)
                except queue.Full:
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queue.put_nowait(data)

                samples = np.frombuffer(
                    data,
                    dtype=np.int16,
                )
                rms = (
                    float(
                        np.sqrt(
                            np.mean(
                                samples.astype(np.float64) ** 2
                            )
                        )
                    )
                    if samples.size
                    else 0.0
                )
                self._publish(
                    "audio.streaming.level",
                    {
                        "rms": rms,
                        "samples": samples[:1024].tolist(),
                    },
                )
            except Exception as exc:
                if self._running:
                    self.last_error = str(exc)
                    self._publish(
                        "audio.error",
                        {
                            "operation": "stream_capture",
                            "error": str(exc),
                        },
                    )
                break

    def _speech_loop(self) -> None:
        pre_roll: deque[bytes] = deque(
            maxlen=self.pre_roll_frames
        )
        utterance: list[bytes] = []
        speaking = False
        silence_frames = 0

        while self._running:
            try:
                frame = self._queue.get(timeout=0.3)
            except queue.Empty:
                continue

            if frame is None:
                break

            speech = self._frame_has_speech(frame)

            if not speaking:
                pre_roll.append(frame)
                if speech:
                    speaking = True
                    silence_frames = 0
                    utterance = list(pre_roll)
                    self._publish(
                        "audio.streaming.speech_started",
                        {},
                    )
                continue

            utterance.append(frame)

            if speech:
                silence_frames = 0
            else:
                silence_frames += 1

            timed_out = (
                len(utterance)
                >= self.max_utterance_frames
            )
            completed = (
                silence_frames
                >= self.silence_frames_required
            )

            if completed or timed_out:
                self._publish(
                    "audio.streaming.speech_ended",
                    {
                        "frames": len(utterance),
                        "timed_out": timed_out,
                    },
                )
                completed_frames = list(utterance)
                self._submit_transcription(completed_frames)
                utterance = []
                pre_roll.clear()
                speaking = False
                silence_frames = 0

    def _frame_has_speech(self, frame: bytes) -> bool:
        vad = getattr(self.voice_service, "vad", None)
        web_rtc = getattr(vad, "_webrtcvad", None)

        if web_rtc is not None:
            try:
                return bool(
                    web_rtc.is_speech(
                        frame,
                        self.sample_rate,
                    )
                )
            except Exception:
                pass

        samples = np.frombuffer(
            frame,
            dtype=np.int16,
        )
        if samples.size == 0:
            return False

        rms = float(
            np.sqrt(
                np.mean(
                    samples.astype(np.float64) ** 2
                )
            )
        )
        threshold = float(
            getattr(vad, "rms_threshold", 350.0)
        )
        return rms >= threshold

    def _submit_transcription(
        self,
        frames: list[bytes],
    ) -> None:
        if not frames:
            return

        # Keep latency predictable. If Whisper is already processing, retain
        # only one queued utterance instead of building a long backlog.
        if self._pending_transcriptions >= 2:
            self._publish(
                "audio.streaming.transcription_dropped",
                {
                    "reason": "transcription_backlog",
                    "frames": len(frames),
                },
            )
            return

        self._pending_transcriptions += 1
        future = self._transcription_executor.submit(
            self._transcribe_utterance,
            frames,
        )
        future.add_done_callback(
            lambda _future: self._transcription_finished()
        )

    def _transcription_finished(self) -> None:
        self._pending_transcriptions = max(
            0,
            self._pending_transcriptions - 1,
        )

    def _transcribe_utterance(
        self,
        frames: list[bytes],
    ) -> None:
        if not frames:
            return

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="buster_stream_",
                suffix=".wav",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

            with wave.open(str(temp_path), "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(b"".join(frames))

            self._publish(
                "audio.streaming.transcription_started",
                {
                    "audio_file": str(temp_path),
                },
            )

            result = self.voice_service.transcribe(
                temp_path,
                language="en",
                require_speech=False,
                fast_mode=True,
            )
            text = str(
                result.get("text", "")
            ).strip()

            payload = {
                **result,
                "text": text,
                "streaming": True,
                "final": True,
            }

            self._publish(
                "audio.streaming.transcription_final",
                payload,
            )

            if text:
                if self.wake_word_service is not None:
                    wake_result = self.wake_word_service.process_transcript(
                        text,
                        source="streaming_stt",
                    )
                    self._publish(
                        "audio.streaming.wake_result",
                        wake_result,
                    )
                else:
                    self._publish(
                        "chat.voice_input",
                        {
                            "text": text,
                            "source": "streaming_stt",
                        },
                    )
        except Exception as exc:
            self.last_error = str(exc)
            self._publish(
                "audio.error",
                {
                    "operation": "stream_transcribe",
                    "error": str(exc),
                },
            )
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def _subscribe_events(self) -> None:
        subscribe = getattr(
            self.dispatcher,
            "subscribe",
            None,
        )
        if not callable(subscribe):
            return

        handlers = {
            "audio.streaming.start.requested": (
                lambda _event: self.start()
            ),
            "audio.streaming.stop.requested": (
                lambda _event: self.stop()
            ),
            "audio.streaming.toggle.requested": (
                self._handle_toggle
            ),
        }

        for topic, handler in handlers.items():
            try:
                unsubscribe = subscribe(
                    topic,
                    handler,
                )
                if callable(unsubscribe):
                    self._subscriptions.append(
                        unsubscribe
                    )
            except Exception:
                continue

    def _handle_toggle(self, _event: Any) -> None:
        if self._running:
            self.stop()
        else:
            self.start()

    def _publish(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> None:
        publish = getattr(
            self.dispatcher,
            "publish",
            None,
        )
        if not callable(publish):
            return

        try:
            publish(
                topic,
                payload,
                source="streaming_stt",
            )
        except TypeError:
            publish(topic, payload)
