from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any


class WakeWordService:
    """Wake-word gate that reuses final Streaming STT transcripts."""

    DEFAULT_WAKE_PHRASES = (
        "hey buster",
        "okay buster",
        "ok buster",
    )

    def __init__(
        self,
        runtime_core: Any,
        *,
        config_path: str | Path | None = None,
        command_window_seconds: float = 8.0,
    ):
        self.runtime_core = runtime_core
        self.dispatcher = getattr(runtime_core, "dispatcher", None)
        self.root = Path(getattr(runtime_core, "root", ".")).resolve()
        self.config_path = Path(
            config_path
            or self.root / "data" / "wake_word_config.json"
        )
        self.command_window_seconds = float(command_window_seconds)
        self.enabled = False
        self.listening_for_command = False
        self.command_window_until = 0.0
        self.last_detected_at = 0.0
        self.last_command = ""
        self.last_error = ""
        self.wake_phrases = list(self.DEFAULT_WAKE_PHRASES)
        self._subscriptions = []
        self._lock = threading.RLock()
        self._load_config()
        self._subscribe_events()

    @property
    def available(self) -> bool:
        return True

    @property
    def configured(self) -> bool:
        return bool(self.wake_phrases)

    @property
    def running(self) -> bool:
        return self.enabled

    @property
    def primary_phrase(self) -> str:
        return self.wake_phrases[0] if self.wake_phrases else "hey buster"

    def status(self) -> dict[str, Any]:
        return {
            "status": "running" if self.enabled else "ready",
            "running": self.enabled,
            "enabled": self.enabled,
            "available": True,
            "configured": self.configured,
            "wake_phrases": list(self.wake_phrases),
            "listening_for_command": self.listening_for_command,
            "command_window_seconds": self.command_window_seconds,
            "last_detected_at": self.last_detected_at,
            "last_command": self.last_command,
            "last_error": self.last_error,
        }

    def enable(self) -> dict[str, Any]:
        with self._lock:
            self.enabled = True
            self._reset_command_window()
        self._publish("audio.wake_word.enabled", self.status())
        self._publish(
            "voice.status",
            {"status": "wake_word_ready", "wake_phrase": self.primary_phrase},
        )
        return self.status()

    def disable(self) -> dict[str, Any]:
        with self._lock:
            self.enabled = False
            self._reset_command_window()
        self._publish("audio.wake_word.disabled", self.status())
        return self.status()

    def toggle(self) -> dict[str, Any]:
        return self.disable() if self.enabled else self.enable()

    def process_transcript(
        self,
        text: str,
        *,
        source: str = "streaming_stt",
    ) -> dict[str, Any]:
        clean_text = self._clean_text(text)
        if not clean_text:
            return {"handled": False, "forward": False, "command": ""}

        with self._lock:
            if not self.enabled:
                return {
                    "handled": False,
                    "forward": True,
                    "command": clean_text,
                    "wake_detected": False,
                }

            now = time.time()
            if self.listening_for_command and now > self.command_window_until:
                self._reset_command_window()
                self._publish(
                    "audio.wake_word.command_timeout",
                    {"wake_phrase": self.primary_phrase},
                )

            wake_match = self._find_wake_phrase(clean_text)
            if wake_match is not None:
                phrase, _start, end = wake_match
                self.last_detected_at = now
                command = clean_text[end:].strip(" ,.!?:;-")
                self._publish(
                    "audio.wake_word.detected",
                    {
                        "wake_phrase": phrase,
                        "transcript": clean_text,
                        "source": source,
                    },
                )

                if command:
                    self._reset_command_window()
                    return self._emit_command(command, source, phrase)

                self.listening_for_command = True
                self.command_window_until = now + self.command_window_seconds
                self._publish(
                    "audio.wake_word.awaiting_command",
                    {
                        "wake_phrase": phrase,
                        "timeout_seconds": self.command_window_seconds,
                    },
                )
                return {
                    "handled": True,
                    "forward": False,
                    "command": "",
                    "wake_detected": True,
                    "awaiting_command": True,
                }

            if self.listening_for_command and now <= self.command_window_until:
                self._reset_command_window()
                return self._emit_command(
                    clean_text,
                    source,
                    self.primary_phrase,
                )

            return {
                "handled": True,
                "forward": False,
                "command": "",
                "wake_detected": False,
            }

    def _emit_command(
        self,
        command: str,
        source: str,
        wake_phrase: str,
    ) -> dict[str, Any]:
        command = command.strip()
        self.last_command = command
        payload = {
            "text": command,
            "command": command,
            "wake_phrase": wake_phrase,
            "source": source,
        }
        self._publish("audio.wake_word.command", payload)
        self._publish("chat.voice_input", payload)
        self._publish("voice.command.received", payload)
        return {
            "handled": True,
            "forward": True,
            "command": command,
            "wake_detected": True,
        }

    def _find_wake_phrase(
        self,
        text: str,
    ) -> tuple[str, int, int] | None:
        normalized = text.lower()
        for phrase in sorted(self.wake_phrases, key=len, reverse=True):
            match = re.search(
                r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)",
                normalized,
            )
            if match:
                return phrase, match.start(), match.end()
        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(str(text or "").strip().split())

    def _reset_command_window(self) -> None:
        self.listening_for_command = False
        self.command_window_until = 0.0

    def _load_config(self) -> None:
        try:
            if not self.config_path.exists():
                self._save_config()
                return
            data = json.loads(
                self.config_path.read_text(encoding="utf-8")
            )
            phrases = data.get("wake_phrases")
            if isinstance(phrases, list):
                cleaned = [
                    self._clean_text(value).lower()
                    for value in phrases
                    if self._clean_text(value)
                ]
                if cleaned:
                    self.wake_phrases = cleaned
            self.command_window_seconds = float(
                data.get(
                    "command_window_seconds",
                    self.command_window_seconds,
                )
            )
            self.enabled = bool(
                data.get("enabled_by_default", False)
            )
        except Exception as exc:
            self.last_error = str(exc)

    def _save_config(self) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(
                    {
                        "wake_phrases": self.wake_phrases,
                        "command_window_seconds": self.command_window_seconds,
                        "enabled_by_default": False,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            self.last_error = str(exc)

    def _subscribe_events(self) -> None:
        subscribe = getattr(self.dispatcher, "subscribe", None)
        if not callable(subscribe):
            return

        handlers = {
            "audio.wake_word.enable.requested": lambda _event: self.enable(),
            "audio.wake_word.disable.requested": lambda _event: self.disable(),
            "audio.wake_word.toggle.requested": lambda _event: self.toggle(),
            "audio.wake_word.status.requested": lambda _event: self._publish(
                "audio.wake_word.status",
                self.status(),
            ),
        }

        for topic, handler in handlers.items():
            try:
                unsubscribe = subscribe(topic, handler)
                if callable(unsubscribe):
                    self._subscriptions.append(unsubscribe)
            except Exception:
                continue

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        publish = getattr(self.dispatcher, "publish", None)
        if not callable(publish):
            return
        try:
            publish(topic, payload, source="wake_word_service")
        except TypeError:
            publish(topic, payload)
